"""Tests for dds_glossary.database module."""

import pytest
from sqlalchemy import inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from dds_glossary.database import (
    get_concept,
    get_concept_collection,
    get_concept_collections,
    get_concept_schemes,
    get_concepts,
    get_in_collections,
    get_in_schemes,
    get_relations,
    init_engine,
    save_dataset,
)
from dds_glossary.model import (
    Concept,
    ConceptCollection,
    ConceptScheme,
    InCollection,
    InScheme,
    SemanticRelation,
    SemanticRelationType,
)

from ..common import add_concept_schemes, add_concepts, add_relations, add_concept_collections


def engine_init_checks(engine: Engine) -> None:
    """Check the engine initialization.

    Args:
        engine (Engine): The database engine.

    Returns:
        None
    """
    assert engine is not None

    inspector = inspect(engine)
    assert inspector.has_table("concept_schemes")
    assert inspector.has_table("concepts")
    assert inspector.has_table("semantic_relations")


def test_init_engine_env_var_not_found(monkeypatch) -> None:
    """Test the init_engine function when the DATABASE_URL environment variable is
    not found."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValueError) as exc_info:
        init_engine()
    assert "DATABASE_URL" in str(exc_info.value)


def test_init_engine_database_not_exists_no_drop() -> None:
    """Test the init_engine function when the database does not exist and
    drop_database_flag is False."""
    engine = init_engine(drop_database_flag=False)
    engine_init_checks(engine)


def test_init_engine_database_not_exists_drop() -> None:
    """Test the init_engine function when the database does not exist and
    drop_database_flag is True."""
    engine = init_engine(drop_database_flag=True)
    engine_init_checks(engine)


def test_init_engine_database_exists_no_drop() -> None:
    """Test the init_engine function when the database exists and
    drop_database_flag is False."""
    engine = init_engine(drop_database_flag=False)
    engine = init_engine(drop_database_flag=False)
    engine_init_checks(engine)


def test_init_engine_database_exists_drop() -> None:
    """Test the init_engine function when the database exists and
    drop_database_flag is True."""
    engine = init_engine(drop_database_flag=False)
    engine = init_engine(drop_database_flag=True)
    engine_init_checks(engine)


def test_save_dataset_with_no_data(engine: Engine) -> None:
    """Test the save_dataset function with empty data."""
    save_dataset(engine, [], [], [], [], [], [])
    with Session(engine) as session:
        assert session.query(ConceptScheme).count() == 0
        assert session.query(Concept).count() == 0
        assert session.query(ConceptCollection).count() == 0
        assert session.query(InCollection).count() == 0
        assert session.query(InScheme).count() == 0
        assert session.query(SemanticRelation).count() == 0


def test_save_dataset_with_data(engine: Engine) -> None:
    """Test the save_dataset function with data."""
    concept_scheme_iri = "http://example.org/concept_scheme"
    concept1_iri = "http://example.org/concept1"
    concept2_iri = "http://example.org/concept2"
    concept_collection_iri = "http://example.org/collection"
    concept_schemes = [
        ConceptScheme(
            iri=concept_scheme_iri,
            notation="Concept Scheme Notation",
            scopeNote="Concept Scheme Scope Note",
            prefLabels=[{"en": "Concept Scheme Pref Label"}],
        )
    ]
    concepts = [
        Concept(
            iri=concept1_iri,
            identifier="Concept1 Identifier",
            notation="Concept Notation",
            prefLabels=[{"en": "Concept1 Pref Label"}],
            altLabels=[{"en": "Concept1 Alt Label"}],
            scopeNotes=["Concept1 Scope Note"],
        ),
        Concept(
            iri=concept2_iri,
            identifier="Concept2 Identifier",
            notation="Concept2 Notation",
            prefLabels=[{"en": "Concept2 Pref Label"}],
            altLabels=[{"en": "Concept2 Alt Label"}],
            scopeNotes=["Concept2 Scope Note"],
        ),
    ]
    concept_collections = [
        ConceptCollection(
            iri=concept_collection_iri,
            notation="Collection Notation",
            prefLabels=[{"en": "Collection Pref Label"}],
        )
    ]
    in_collections = [
        InCollection(
            member_iri=concepts[0].iri,
            collection_iri=concept_collections[0].iri,
        )
    ]
    in_schemes = [
        InScheme(
            member_iri=concepts[0].iri,
            scheme_iri=concept_schemes[0].iri,
        ),
        InScheme(
            member_iri=concepts[1].iri,
            scheme_iri=concept_schemes[0].iri,
        ),
    ]
    semantic_relations = [
        SemanticRelation(
            type=SemanticRelationType.BROADER,
            source_concept_iri=concepts[0].iri,
            target_concept_iri=concepts[1].iri,
        )
    ]
    save_dataset(
        engine=engine,
        concept_schemes=concept_schemes,
        concepts=concepts,
        concepts_collections=concept_collections,
        in_schemes=in_schemes,
        in_collections=in_collections,
        semantic_relations=semantic_relations,
    )

    with Session(engine) as session:
        assert session.query(ConceptScheme).count() == 1
        assert session.query(Concept).count() == 2
        assert session.query(ConceptCollection).count() == 1
        assert session.query(InCollection).count() == 1
        assert session.query(SemanticRelation).count() == 1
        assert session.query(ConceptScheme).one().iri == concept_scheme_iri
        assert session.query(Concept).all()[0].iri == concept1_iri
        assert session.query(ConceptCollection).one().iri == concept_collection_iri
        assert session.query(InCollection).one().member_iri == concept1_iri
        assert session.query(SemanticRelation).one().source_concept_iri == concept1_iri
        assert session.query(SemanticRelation).one().target_concept_iri == concept2_iri


def test_get_concept_scheme(engine: Engine) -> None:
    """Test the get_concept_schemes."""
    concept_schemes_dicts = add_concept_schemes(engine, 1)

    concept_schemes = get_concept_schemes(engine)
    assert len(concept_schemes) == len(concept_schemes_dicts)
    assert concept_schemes[0].to_dict() == concept_schemes_dicts[0]


def test_get_concepts(engine: Engine) -> None:
    """Test the get_concepts."""
    concept_schemes_dict = add_concept_schemes(engine, 1)
    concepts_dict, _ = add_concepts(engine, [(0, concept_schemes_dict[0]["iri"])])

    concepts = get_concepts(engine, concept_schemes_dict[0]["iri"])
    assert len(concepts) == len(concepts_dict)
    assert concepts[0].to_dict() == concepts_dict[0]


def test_get_concept_collections(engine: Engine) -> None:
    """Test the get_concept_collections."""
    concept_collections_dict = add_concept_collections(engine, 1)

    concept_collections = get_concept_collections(engine, concept_collections_dict[0]["iri"])
    assert len(concept_collections) == len(concept_collections_dict)
    assert concept_collections[0].to_dict() == concept_collections_dict[0]


def test_get_concept(engine: Engine) -> None:
    """Test the get_concept."""
    concept_schemes_dict = add_concept_schemes(engine, 1)
    concepts_dict, _ = add_concepts(engine, [(0, concept_schemes_dict[0]["iri"])])

    concept = get_concept(engine, concepts_dict[0]["iri"])
    assert concept is not None
    assert concept.to_dict() == concepts_dict[0]


def test_get_in_schemes(engine: Engine) -> None:
    """Test the get_in_schemes."""
    concept_schemes_dict = add_concept_schemes(engine, 1)
    concepts_dict, in_schemes_list = add_concepts(
        engine, [(0, concept_schemes_dict[0]["iri"])]
    )

    in_schemes = get_in_schemes(engine, concepts_dict[0]["iri"])
    assert len(in_schemes) == len(in_schemes_list)
    assert [in_scheme.scheme_iri for in_scheme in in_schemes] == in_schemes_list


def test_get_relations(engine: Engine) -> None:
    """Test the get_relations."""
    concept_schemes_dict = add_concept_schemes(engine, 1)
    scheme_iri = concept_schemes_dict[0]["iri"]
    concepts_dict, _ = add_concepts(engine, [(0, scheme_iri), (1, scheme_iri)])
    relations_dict = add_relations(
        engine, [(concepts_dict[0]["iri"], concepts_dict[1]["iri"])]
    )

    relations = get_relations(engine, concepts_dict[0]["iri"])
    assert len(relations) == len(relations_dict)
    assert relations[0].to_dict() == relations_dict[0]
