import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services import semantic_runtime as runtime


@pytest.fixture(autouse=True)
def isolated_models(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runtime, "_models", {})
    monkeypatch.setattr(runtime, "_failed_paths", set())
    runtime._get_runtime.cache_clear()


def write_cached_model(directory: Path) -> Path:
    model_dir = directory / runtime._MODEL_DIRECTORY
    for name in runtime._REQUIRED_FILES:
        target = model_dir / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"fixture")
    (model_dir / runtime._READY_FILE).write_text(json.dumps({
        "model_id": runtime.MODEL_ID,
        "revision": runtime.MODEL_REVISION,
        "file_sizes": {name: 7 for name in runtime._REQUIRED_FILES},
    }), encoding="utf-8")
    return model_dir


class FakeEmbedding:
    def __init__(self, **kwargs):
        self.options = kwargs
        self.inputs = []

    def embed(self, texts, **kwargs):
        self.inputs.append((texts, kwargs))
        for _text in texts:
            yield [3.0, 4.0] + [0.0] * (runtime.MODEL_DIMENSION - 2)


def test_missing_model_never_imports_or_downloads(tmp_path, monkeypatch):
    def unexpected_import():
        raise AssertionError("Missing model must fail before loading inference dependencies")

    monkeypatch.setattr(runtime, "_embedding_class", unexpected_import)
    instance = runtime.get_runtime(tmp_path)
    assert instance.encode_queries([]) == []
    with pytest.raises(runtime.SemanticModelNotReadyError):
        instance.encode_queries(["机器人控制"])
    assert not tmp_path.joinpath(runtime._MODEL_DIRECTORY).exists()


def test_status_only_checks_files_and_honors_configured_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("SEMANTIC_MODEL_CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(runtime, "_dependency_status", lambda: True)

    def unexpected_import():
        raise AssertionError("Status must not load inference dependencies")

    monkeypatch.setattr(runtime, "_embedding_class", unexpected_import)
    write_cached_model(tmp_path)
    status = runtime.model_status()
    assert status["cache_dir"] == str(tmp_path.resolve())
    assert status["model_cached"] is True
    assert status["loaded"] is False
    assert runtime.get_runtime().cache_dir == tmp_path.resolve()


def test_cached_model_uses_local_cpu_only_and_normalizes_prefixes(tmp_path, monkeypatch):
    model_dir = write_cached_model(tmp_path)
    factories = []

    def factory(**kwargs):
        model = FakeEmbedding(**kwargs)
        factories.append(model)
        return model

    monkeypatch.setattr(runtime, "_embedding_class", lambda: factory)
    first = runtime.LocalSemanticRuntime(tmp_path, threads=99, batch_size=99)
    second = runtime.LocalSemanticRuntime(tmp_path, threads=4, batch_size=1)
    expected = [0.6, 0.8] + [0.0] * (runtime.MODEL_DIMENSION - 2)
    assert first.encode_queries(["  机器人控制  "]) == [expected]
    assert second.encode_passages(["Cable-driven continuum robot"]) == [expected]
    assert len(factories) == 1
    model = factories[0]
    assert model.options["local_files_only"] is True
    assert model.options["specific_model_path"] == str(model_dir.resolve())
    assert model.options["providers"] == ["CPUExecutionProvider"]
    assert model.options["threads"] == 4
    assert model.inputs[0] == (["query: 机器人控制"], {"batch_size": 32, "parallel": None})
    assert model.inputs[1][0] == ["passage: Cable-driven continuum robot"]


def test_explicit_prepare_is_only_download_path_and_reuses_verified_files(tmp_path, monkeypatch):
    downloads = []
    phases = []

    def download(**kwargs):
        downloads.append(kwargs)
        model_dir = kwargs["local_dir"]
        for name in kwargs["allow_patterns"]:
            target = model_dir / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"downloaded")

    monkeypatch.setattr(runtime, "_dependency_status", lambda: True)
    monkeypatch.setattr(runtime, "_embedding_class", lambda: FakeEmbedding)
    monkeypatch.setitem(sys.modules, "huggingface_hub", SimpleNamespace(snapshot_download=download))
    instance = runtime.get_runtime(tmp_path)
    instance.prepare_model(progress_callback=phases.append)
    instance.prepare_model(progress_callback=phases.append)
    assert len(downloads) == 1
    assert downloads[0]["repo_id"] == runtime.MODEL_ID
    assert downloads[0]["revision"] == runtime.MODEL_REVISION
    assert phases == ["downloading", "loading", "ready", "loading", "ready"]
    assert instance.status()["model_cached"] is True


def test_missing_dependency_is_clear_and_does_not_create_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, "_dependency_status", lambda: False)
    with pytest.raises(runtime.SemanticDependencyError, match="requirements-semantic.txt"):
        runtime.get_runtime(tmp_path).prepare_model()
    assert not tmp_path.joinpath(runtime._MODEL_DIRECTORY).exists()


def test_corrupt_cached_files_fail_before_model_loading(tmp_path, monkeypatch):
    model_dir = write_cached_model(tmp_path)
    (model_dir / "onnx/model.onnx").write_bytes(b"truncated")
    monkeypatch.setattr(runtime, "_dependency_status", lambda: True)
    assert runtime.model_status(tmp_path)["model_cached"] is False
    with pytest.raises(runtime.SemanticModelNotReadyError):
        runtime.get_runtime(tmp_path).encode_passages(["robot"])
    (model_dir / runtime._READY_FILE).write_text("[]", encoding="utf-8")
    assert runtime.model_status(tmp_path)["model_cached"] is False


def test_lock_covers_lazy_generator_consumption(tmp_path):
    model_dir = write_cached_model(tmp_path)

    class ObservedLock:
        held = False

        def __enter__(self):
            self.held = True

        def __exit__(self, *_args):
            self.held = False

    lock = ObservedLock()

    class LazyEmbedding:
        def embed(self, _texts, **_kwargs):
            assert lock.held, "The generator must be consumed under the inference lock"
            yield [1.0] + [0.0] * (runtime.MODEL_DIMENSION - 1)
            assert lock.held

    runtime._models[(str(model_dir.resolve()), 2)] = (LazyEmbedding(), lock)
    result = runtime.get_runtime(tmp_path).encode_queries(["robot"])
    assert len(result) == 1
    assert lock.held is False


@pytest.mark.parametrize("invalid", [[0.0] * 384, [float("nan")] * 384, [1.0] * 3])
def test_invalid_embedding_fails_clearly(invalid):
    with pytest.raises(runtime.SemanticModelError):
        runtime._normalize_embedding(invalid)


def test_same_size_model_corruption_load_failure_requires_forced_repair(tmp_path, monkeypatch):
    model_dir = write_cached_model(tmp_path)
    # File-size checks alone cannot detect this kind of corrupted download.
    (model_dir / "onnx/model.onnx").write_bytes(b"corrupt")
    assert runtime.model_status(tmp_path)["model_cached"] is True

    def failed_load(**_kwargs):
        raise ValueError("Invalid ONNX graph")

    monkeypatch.setattr(runtime, "_embedding_class", lambda: failed_load)
    instance = runtime.get_runtime(tmp_path)
    with pytest.raises(runtime.SemanticModelError, match="加载失败"):
        instance.encode_queries(["robot"])
    assert (model_dir / runtime._FAILED_FILE).is_file()
    assert instance.status()["model_cached"] is False
    assert instance.status()["loaded"] is False

    downloads = []

    def repair_download(**kwargs):
        downloads.append(kwargs)
        write_cached_model(tmp_path)

    monkeypatch.setattr(runtime, "_dependency_status", lambda: True)
    monkeypatch.setattr(runtime, "_embedding_class", lambda: FakeEmbedding)
    monkeypatch.setitem(sys.modules, "huggingface_hub", SimpleNamespace(
        snapshot_download=repair_download,
    ))
    # Even across restarts, the failure marker must trigger a fresh download.
    runtime._failed_paths.clear()
    assert instance.prepare_model()["model_cached"] is True
    assert downloads[0]["force_download"] is True
    assert not (model_dir / runtime._FAILED_FILE).exists()
    assert len(instance.encode_queries(["robot"])) == 1


def test_inference_failure_invalidates_and_evicts_cached_model(tmp_path, monkeypatch):
    model_dir = write_cached_model(tmp_path)

    class FailedInference(FakeEmbedding):
        def embed(self, _texts, **_kwargs):
            raise RuntimeError("Inference failed")

    monkeypatch.setattr(runtime, "_embedding_class", lambda: FailedInference)
    instance = runtime.get_runtime(tmp_path)
    with pytest.raises(runtime.SemanticModelError, match="编码失败"):
        instance.encode_passages(["robot"])
    assert (model_dir / runtime._FAILED_FILE).exists()
    assert instance.status()["model_cached"] is False
    assert not runtime._models
    with pytest.raises(runtime.SemanticModelNotReadyError):
        instance.encode_passages(["robot"])
