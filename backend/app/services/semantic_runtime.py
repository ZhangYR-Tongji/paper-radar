"""CPU-only multilingual embeddings, with explicit downloads and offline inference.

The E5 model uses mean pooling and L2 normalization. Research descriptions use
the ``query: `` prefix; paper titles and abstracts use ``passage: ``. This module
does not import the optional inference dependencies until a model is requested.
"""

import importlib.util
import json
import math
import os
import threading
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path
from typing import Any

MODEL_ID = "intfloat/multilingual-e5-small"
MODEL_REVISION = "614241f622f53c4eeff9890bdc4f31cfecc418b3"
MODEL_DIMENSION = 384
MODEL_MAX_TOKENS = 512
_MODEL_DIRECTORY = f"multilingual-e5-small-{MODEL_REVISION[:12]}"
_READY_FILE = "paper-radar-model.json"
_REQUIRED_FILES = (
    "config.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "onnx/model.onnx",
)
_models: dict[tuple[str, int], tuple[Any, Any]] = {}
_model_lock = threading.RLock()
_prepare_lock = threading.Lock()


class SemanticRuntimeError(RuntimeError):
    """Semantic inference is unavailable; callers may retain keyword ranking."""


class SemanticDependencyError(SemanticRuntimeError):
    """The optional local inference dependencies are missing or cannot load."""


class SemanticModelNotReadyError(SemanticRuntimeError):
    """The pinned model has not been explicitly downloaded and verified."""


class SemanticModelError(SemanticRuntimeError):
    """A model download, load, or inference failed."""


def default_model_cache_dir() -> Path:
    """Keep models outside the repository and application database."""
    configured = os.environ.get("SEMANTIC_MODEL_CACHE_DIR", "").strip()
    if configured:
        return Path(configured).expanduser()
    # USERPROFILE stays stable across the packaged editor and desktop launcher;
    # LOCALAPPDATA can be virtualized into the editor's package-local cache.
    return Path.home() / ".cache" / "paper-radar" / "models"


def _cache_path(cache_dir: str | Path | None) -> Path:
    return Path(cache_dir or default_model_cache_dir()).expanduser().resolve()


def _dependency_status() -> bool:
    return all(
        importlib.util.find_spec(module) is not None
        for module in ("fastembed", "onnxruntime", "huggingface_hub")
    )


def _cache_valid(model_dir: Path) -> bool:
    try:
        metadata = json.loads((model_dir / _READY_FILE).read_text(encoding="utf-8"))
        if not isinstance(metadata, dict):
            return False
        if metadata.get("model_id") != MODEL_ID or metadata.get("revision") != MODEL_REVISION:
            return False
        sizes = metadata["file_sizes"]
        return all(
            (model_dir / name).is_file()
            and (model_dir / name).stat().st_size == sizes[name]
            and sizes[name] > 0
            for name in _REQUIRED_FILES
        )
    except (OSError, ValueError, KeyError, TypeError):
        return False


def model_status(cache_dir: str | Path | None = None) -> dict[str, Any]:
    """Inspect readiness without loading a model or making network requests."""
    cache = _cache_path(cache_dir)
    model_dir = cache / _MODEL_DIRECTORY
    with _model_lock:
        loaded = any(key[0] == str(model_dir) for key in _models)
    return {
        "model_id": MODEL_ID,
        "revision": MODEL_REVISION,
        "dimension": MODEL_DIMENSION,
        "max_tokens": MODEL_MAX_TOKENS,
        "cache_dir": str(cache),
        "model_dir": str(model_dir),
        "dependencies_installed": _dependency_status(),
        "model_cached": _cache_valid(model_dir),
        "loaded": loaded,
    }


def _embedding_class() -> Any:
    try:
        from fastembed import TextEmbedding
        from fastembed.common.model_description import ModelSource, PoolingType
    except (ImportError, OSError) as exc:
        raise SemanticDependencyError(
            "本地语义依赖不可用，请在后端 Python 环境运行 "
            "python -m pip install -r requirements-semantic.txt。"
        ) from exc
    # FastEmbed officially documents E5-small as a custom ONNX model.
    if not any(item["model"] == MODEL_ID for item in TextEmbedding.list_supported_models()):
        TextEmbedding.add_custom_model(
            model=MODEL_ID,
            pooling=PoolingType.MEAN,
            normalization=True,
            sources=ModelSource(hf=MODEL_ID),
            dim=MODEL_DIMENSION,
            model_file="onnx/model.onnx",
            license="mit",
            size_in_gb=0.47,
        )
    return TextEmbedding


def _normalize_embedding(vector: Any) -> list[float]:
    result = [float(value) for value in vector]
    if len(result) != MODEL_DIMENSION or not all(math.isfinite(value) for value in result):
        raise SemanticModelError("本地语义模型返回了无效向量。")
    norm = math.sqrt(sum(value * value for value in result))
    if norm <= 0:
        raise SemanticModelError("本地语义模型返回了空向量。")
    return [value / norm for value in result]


class LocalSemanticRuntime:
    def __init__(
        self,
        cache_dir: str | Path | None = None,
        *,
        threads: int = 2,
        batch_size: int = 16,
    ) -> None:
        self.cache_dir = _cache_path(cache_dir)
        self.model_dir = self.cache_dir / _MODEL_DIRECTORY
        # Bound CPU and memory use even when callers supply larger values.
        self.threads = max(1, min(int(threads), 4))
        self.batch_size = max(1, min(int(batch_size), 32))

    def status(self) -> dict[str, Any]:
        return model_status(self.cache_dir)

    def _load_model(self, *, verifying_download: bool = False) -> tuple[Any, Any]:
        if not verifying_download and not _cache_valid(self.model_dir):
            raise SemanticModelNotReadyError(
                "本地语义模型尚未准备好，请在设置中点击下载并准备模型。"
            )
        key = (str(self.model_dir), self.threads)
        with _model_lock:
            if key not in _models:
                embedding_class = _embedding_class()
                try:
                    # A concrete local directory bypasses hub/cache resolution entirely.
                    model = embedding_class(
                        model_name=MODEL_ID,
                        cache_dir=str(self.cache_dir),
                        specific_model_path=str(self.model_dir),
                        local_files_only=True,
                        providers=["CPUExecutionProvider"],
                        threads=self.threads,
                        enable_cpu_mem_arena=False,
                    )
                except Exception as exc:
                    raise SemanticModelError(
                        "本地语义模型加载失败，请重新准备模型或检查缓存目录权限。"
                    ) from exc
                _models[key] = (model, threading.Lock())
            return _models[key]

    def prepare_model(
        self,
        *,
        force_download: bool = False,
        progress_callback: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        """Explicitly download the pinned public model, then verify offline loading.

        This is the only method that may access the network. Reusing a verified
        local model performs no download. Interrupted downloads can be resumed.
        """
        with _prepare_lock:
            if not _dependency_status():
                raise SemanticDependencyError(
                    "请先安装本地语义依赖：python -m pip install -r requirements-semantic.txt。"
                )
            if force_download or not _cache_valid(self.model_dir):
                try:
                    from huggingface_hub import snapshot_download

                    if progress_callback:
                        progress_callback("downloading")
                    self.model_dir.mkdir(parents=True, exist_ok=True)
                    snapshot_download(
                        repo_id=MODEL_ID,
                        revision=MODEL_REVISION,
                        allow_patterns=list(_REQUIRED_FILES),
                        local_dir=self.model_dir,
                        max_workers=2,
                        force_download=force_download,
                    )
                except Exception as exc:
                    raise SemanticModelError(
                        "语义模型下载失败，请检查网络后重试；已下载的文件会保留。"
                    ) from exc
                with _model_lock:
                    for key in [key for key in _models if key[0] == str(self.model_dir)]:
                        del _models[key]
                if progress_callback:
                    progress_callback("loading")
                model, inference_lock = self._load_model(verifying_download=True)
                try:
                    with inference_lock:
                        vectors = list(model.embed(["query: model readiness"], batch_size=1))
                    _normalize_embedding(vectors[0])
                    metadata = {
                        "model_id": MODEL_ID,
                        "revision": MODEL_REVISION,
                        "file_sizes": {
                            name: (self.model_dir / name).stat().st_size
                            for name in _REQUIRED_FILES
                        },
                    }
                    temporary = self.model_dir / f"{_READY_FILE}.tmp"
                    temporary.write_text(json.dumps(metadata), encoding="utf-8")
                    temporary.replace(self.model_dir / _READY_FILE)
                except Exception as exc:
                    raise SemanticModelError(
                        "语义模型验证失败，请重新下载模型。"
                    ) from exc
            else:
                if progress_callback:
                    progress_callback("loading")
                self._load_model()
            if progress_callback:
                progress_callback("ready")
            return self.status()

    def _encode(self, texts: list[str], prefix: str) -> list[list[float]]:
        if not texts:
            return []
        if any(not isinstance(text, str) or not text.strip() for text in texts):
            raise ValueError("语义编码需要非空文本。")
        model, inference_lock = self._load_model()
        try:
            with inference_lock:
                return [
                    _normalize_embedding(vector)
                    for vector in model.embed(
                        [f"{prefix}: {text.strip()}" for text in texts],
                        batch_size=self.batch_size,
                        parallel=None,
                    )
                ]
        except SemanticRuntimeError:
            raise
        except Exception as exc:
            raise SemanticModelError("本地语义编码失败，请检查模型状态。") from exc

    def encode_queries(self, texts: list[str]) -> list[list[float]]:
        return self._encode(texts, "query")

    def encode_passages(self, texts: list[str]) -> list[list[float]]:
        return self._encode(texts, "passage")


@lru_cache(maxsize=4)
def _get_runtime(cache_dir: str, threads: int, batch_size: int) -> LocalSemanticRuntime:
    return LocalSemanticRuntime(cache_dir, threads=threads, batch_size=batch_size)


def get_runtime(
    cache_dir: str | Path | None = None,
    *,
    threads: int = 2,
    batch_size: int = 16,
) -> LocalSemanticRuntime:
    """Return a shared runtime without importing inference packages or loading weights."""
    return _get_runtime(str(_cache_path(cache_dir)), threads, batch_size)
