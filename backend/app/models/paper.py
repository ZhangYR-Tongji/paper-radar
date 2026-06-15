from sqlalchemy import JSON, Column, Date, Float, ForeignKey, Integer, String, Text

from app.db.session import Base
from app.models.mixins import IdMixin, TimestampMixin


class Paper(IdMixin, TimestampMixin, Base):
    __tablename__ = "papers"

    title = Column(Text, nullable=False)
    normalized_title = Column(Text, index=True, nullable=False)
    abstract = Column(Text, default="", nullable=False)
    authors = Column(JSON, default=list, nullable=False)
    published_date = Column(Date, nullable=True)
    updated_date = Column(Date, nullable=True)
    source = Column(String(64), index=True, nullable=False)
    source_id = Column(String(256), index=True, nullable=True)
    doi = Column(String(256), index=True, nullable=True)
    arxiv_id = Column(String(128), index=True, nullable=True)
    url = Column(Text, nullable=True)
    pdf_url = Column(Text, nullable=True)
    venue = Column(String(256), nullable=True)
    journal = Column(String(256), nullable=True)
    conference = Column(String(256), nullable=True)
    year = Column(Integer, index=True, nullable=True)


class PaperFeature(IdMixin, TimestampMixin, Base):
    __tablename__ = "paper_features"

    paper_id = Column(Integer, ForeignKey("papers.id"), unique=True, index=True, nullable=False)
    matched_keyword_groups = Column(JSON, default=list, nullable=False)
    matched_positive_keywords = Column(JSON, default=list, nullable=False)
    matched_negative_keywords = Column(JSON, default=list, nullable=False)
    topic_tags = Column(JSON, default=list, nullable=False)
    method_tags = Column(JSON, default=list, nullable=False)
    venue_score = Column(Float, default=0.0, nullable=False)
    topic_score = Column(Float, default=0.0, nullable=False)
    method_score = Column(Float, default=0.0, nullable=False)
    freshness_score = Column(Float, default=0.0, nullable=False)
    user_preference_score = Column(Float, default=0.0, nullable=False)
    negative_filter_penalty = Column(Float, default=0.0, nullable=False)
    final_score = Column(Float, default=0.0, index=True, nullable=False)
    classification = Column(String(64), index=True, nullable=False)
