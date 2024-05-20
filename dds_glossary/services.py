"""Services classes and utils for the dds_glossary package."""

from http import HTTPStatus
from pathlib import Path
from typing import ClassVar

from appdirs import user_data_dir
from defusedxml.lxml import parse as parse_xml
from fastapi import HTTPException
from fastapi.templating import Jinja2Templates
from owlready2 import get_ontology, onto_path
from sqlalchemy import Engine

from .database import (
    get_collection,
    get_concept,
    get_concept_scheme,
    get_concept_schemes,
    get_relations,
    init_engine,
    save_dataset,
    search_database,
)
from .model import (
    Collection,
    Concept,
    ConceptScheme,
    Dataset,
    FailedDataset,
    SemanticRelation,
)
from .schema import (
    CollectionResponse,
    ConceptResponse,
    ConceptSchemeResponse,
    EntityResponse,
    FullConeptResponse,
    InitDatasetsResponse,
    RelationResponse,
)


class GlossaryController:
    """
    Controller for the glossary.

    Attributes:
        engine (Engine): The database engine.
        data_dir (Path): The data directory for saving the datasets.
    """

    europa_url: ClassVar[str] = "http://publications.europa.eu/resource/distribution/"
    fao_url: ClassVar[str] = (
        "https://storage.googleapis.com/fao-datalab-caliper/Downloads/"
    )
    datasets: ClassVar[list[Dataset]] = [
        Dataset(
            name="ESTAT-CN2024.rdf",
            url=(
                europa_url
                + "combined-nomenclature-2024/20240425-0/rdf/skos_core/ESTAT-CN2024.rdf"
            ),
        ),
        Dataset(
            name="ESTAT-LoW2015.rdf",
            url=europa_url + "low2015/20240425-0/rdf/skos_core/ESTAT-LoW2015.rdf",
        ),
        Dataset(
            name="ESTAT-NACE2.1.rdf",
            url=(europa_url + "nace2.1/20240425-0/rdf/skos_core/ESTAT-NACE2.1.rdf"),
        ),
        Dataset(
            name="ESTAT-ICST-COM.rdf",
            url=(europa_url + "icst-com/20240425-0/rdf/skos_core/ESTAT-ICST-COM.rdf"),
        ),
        Dataset(
            name="ESTAT-PRODCOM2023.rdf",
            url=(
                europa_url
                + "prodcom2023/20240425-0/rdf/skos_core/ESTAT-PRODCOM2023.rdf"
            ),
        ),
        Dataset(name="ISIC4.rdf", url=fao_url + "ISICRev4/ISIC4.rdf"),
    ]

    def __init__(
        self,
        data_dir_path: str | Path = user_data_dir("dds_glossary", "dds_glossary"),
        engine: Engine | None = None,
    ) -> None:
        self.engine = engine if engine else init_engine()
        self.data_dir = Path(data_dir_path)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        onto_path.append(str(self.data_dir))

    def parse_dataset(
        self,
        dataset_path: Path,
    ) -> tuple[
        list[ConceptScheme],
        list[Concept],
        list[Collection],
        list[SemanticRelation],
    ]:
        """
        Parse a dataset.

        Args:
            dataset_path (Path): The dataset path.

        Returns:
            tuple[list[ConceptScheme], list[Concept], list[Collection],
                list[SemanticRelation]]: The concept schemes, concepts, collections,
                and semantic relations.
        """
        root = parse_xml(dataset_path).getroot()
        concept_scheme_elements = root.findall("core:ConceptScheme", root.nsmap)
        collection_elements = root.findall("core:Collection", root.nsmap)
        concept_elements = root.findall("core:Concept", root.nsmap)
        concept_schemes = [
            ConceptScheme.from_xml_element(concept_scheme_element)
            for concept_scheme_element in concept_scheme_elements
        ]
        concepts = [
            Concept.from_xml_element(concept_element, concept_schemes)
            for concept_element in concept_elements
        ]
        collections = [
            Collection.from_xml_element(collection_element, concept_schemes)
            for collection_element in collection_elements
        ]
        semantic_relations: list[SemanticRelation] = []
        for concept_element in concept_elements:
            semantic_relations.extend(
                SemanticRelation.from_xml_element(concept_element)
            )
        return concept_schemes, concepts, collections, semantic_relations

    def init_datasets(
        self,
        reload: bool = False,
    ) -> InitDatasetsResponse:
        """
        Download and save the datasets, if they do not exist or if the reload flag is
        set.

        Args:
            reload (bool): Flag to reload the datasets. Defaults to False.

        Returns:
            InitDatasetsResponse: The response with the saved and failed datasets.
        """
        saved_datasets: list[Dataset] = []
        failed_datasets: list[FailedDataset] = []
        self.engine = init_engine(drop_database_flag=True)
        for dataset in self.datasets:
            dataset_path = self.data_dir / dataset.name
            try:
                ontology = get_ontology(dataset.url).load(reload=reload)
                ontology.save(file=str(dataset_path), format="rdfxml")
                save_dataset(self.engine, *self.parse_dataset(dataset_path))
                saved_datasets.append(
                    Dataset(
                        name=dataset.name,
                        url=dataset.url,
                    )
                )
            except Exception as error:  # pylint: disable=broad-except
                failed_datasets.append(
                    FailedDataset(
                        name=dataset.name,
                        url=dataset.url,
                        error=str(error),
                    )
                )
        return InitDatasetsResponse(
            saved_datasets=saved_datasets,
            failed_datasets=failed_datasets,
        )

    def get_concept_schemes(self, lang: str = "en") -> list[ConceptSchemeResponse]:
        """
        Get the concept schemes.

        Args:
            lang (str): The language. Defaults to "en".

        Returns:
            list[ConceptSchemeResponse]: The concept schemes.
        """
        return [
            ConceptSchemeResponse(**concept_scheme.to_dict(lang=lang))
            for concept_scheme in get_concept_schemes(self.engine)
        ]

    def get_concepts(self, concept_scheme_iri: str, lang: str = "en") -> list[dict]:
        """
        Get the concepts.

        Args:
            concept_scheme_iri (str): The concept scheme IRI.
            lang (str): The language. Defaults to "en".

        Returns:
            list[dict]: The concepts as dictionaries.

        Raises:
            HTTPException: If the concept scheme is not found.
        """
        concept_scheme = get_concept_scheme(self.engine, concept_scheme_iri)

        if concept_scheme:
            return [concept.to_dict(lang=lang) for concept in concept_scheme.members]
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Concept scheme {concept_scheme_iri} not found.",
        )

    def get_collection(
        self, collection_iri: str, lang: str = "en"
    ) -> CollectionResponse:
        """
        Get the collection.

        Args:
            collection_iri (str): The collection IRI.
            lang (str): The language. Defaults to "en".

        Returns:
            CollectionResponse: The collection with its members.

        Raises:
            HTTPException: If the collection is not found.
        """
        collection = get_collection(self.engine, collection_iri)

        if collection:
            return CollectionResponse(
                **collection.to_dict(lang=lang),
                members=[
                    EntityResponse(**member.to_dict(lang=lang))
                    for member in collection.members
                ],
            )
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Collection {collection_iri} not found.",
        )

    def get_concept(self, concept_iri: str, lang: str = "en") -> FullConeptResponse:
        """
        Get the concept and al its relations.

        Args:
            concept_iri (str): The concept IRI.
            lang (str): The language. Defaults to "en".

        Returns:
            FullConeptResponse: The concept with its concept schemes and relations.

        Raises:
            HTTPException: If the concept is not found.
        """
        concept = get_concept(self.engine, concept_iri)

        if concept:
            return FullConeptResponse(
                **concept.to_dict(lang=lang),
                concept_schemes=[scheme.iri for scheme in concept.concept_schemes],
                relations=[
                    RelationResponse(**relation.to_dict())
                    for relation in get_relations(self.engine, concept_iri)
                ],
            )
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Concept {concept_iri} not found.",
        )

    def search_database(
        self, search_term: str, lang: str = "en"
    ) -> list[ConceptResponse]:
        """
        Search the database for concepts that match the `search_term` in the
        selected `lang`.

        Args:
            search_term (str): The search term to match against.
            lang (str): The language to use for matching. Defaults to "en".

        Returns:
            list[ConceptResponse]: The result concepts matching the `search_term`.
        """
        return [
            ConceptResponse(**concept.to_dict(lang=lang))
            for concept in search_database(self.engine, search_term, lang=lang)
        ]


def get_controller() -> GlossaryController:
    """
    Get the glossary controller.

    Returns:
        GlossaryController: The glossary controller.
    """
    return GlossaryController()


def get_templates() -> Jinja2Templates:
    """
    Get the Jinja2 templates.

    Returns:
        Jinja2Templates: The Jinja2 templates.
    """
    return Jinja2Templates(directory="templates")
