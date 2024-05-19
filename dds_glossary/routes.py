"""Routes for the dds_glossary server."""

from http import HTTPStatus

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.templating import _TemplateResponse

from .auth import get_api_key
from .schema import (
    CollectionResponse,
    ConceptResponse,
    ConceptSchemeResponse,
    FullConeptResponse,
    InitDatasetsResponse,
    VersionResponse,
)

router = APIRouter()


@router.get("/")
def home(
    request: Request,
    search_term: str = "",
    concept_scheme_iri: str = "",
    lang: str = "en",
) -> _TemplateResponse:
    """Get the home page.
    If a `search_term` term is provided, it will filter the concepts by the search term.
    If a `concept_scheme_iri` is provided, it will filter the concepts by the concept
    scheme.

    Args:
        request (Request): The request.
        search_term (str): The search term to filter the concepts. Defaults to "".
        concept_scheme_iri (str): The concept scheme IRI to filter the concepts.
            Defaults to "".
        lang (str): The language to use for searching concepts. Defaults to "en".

    Returns:
        _TemplateResponse: The home page with search results if any.
    """
    if concept_scheme_iri:
        concepts = request.app.state.controller.get_concepts(
            concept_scheme_iri, lang=lang
        )
    else:
        concepts = request.app.state.controller.search_database(search_term, lang=lang)

    return request.app.state.templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "schemes": request.app.state.controller.get_concept_schemes(lang=lang),
            "concepts": concepts,
        },
    )


@router.get("/status")
def status() -> RedirectResponse:
    """Redirect to the status page."""
    return RedirectResponse(url="https://sentier.instatus.com/")


@router.get("/search")
def search(
    request: Request,
    search_term: str,
    lang: str = "en",
) -> list[ConceptResponse]:
    """Search concepts according to given expression.
    Note: This will be removed once #35 (Add elasticsearch) is closed.

    Args:
        search_term (str): The search term to filter the concepts.
        lang (str): The language to use for searching concepts. Defaults to "en".

    Returns:
        list[ConceptResponse]: The search results, if any.
    """
    return request.app.state.controller.search_database(search_term, lang=lang)


@router.get("/version")
def get_version() -> VersionResponse:
    """Get the version of the server.

    Returns:
        VersionResponse: The version of the server.
    """
    return VersionResponse()


@router.post("/init_datasets")
def init_datasets(
    request: Request,
    _api_key: dict = Depends(get_api_key),
    reload: bool = False,
) -> InitDatasetsResponse:
    """Initialize the datasets.

    Args:
        _api_key (dict): The API key.
        reload (bool): Flag to reload the datasets. Defaults to False.

    Returns:
        InitDatasetsResponse: The response.
    """
    return request.app.state.controller.init_datasets(reload=reload)


@router.get("/schemes")
def get_concept_schemes(
    request: Request, lang: str = "en"
) -> list[ConceptSchemeResponse]:
    """
    Returns all the saved concept schemes.

    Args:
        lang (str): The language. Defaults to "en".

    Returns:
        list[ConceptSchemeResponse]: The concept schemes.
    """
    return request.app.state.controller.get_concept_schemes(lang=lang)


@router.get("/concepts")
def get_concepts(
    request: Request, concept_scheme_iri: str, lang: str = "en"
) -> JSONResponse:
    """
    Returns all the saved concepts for a concept scheme.

    Args:
        concept_scheme_iri (str): The concept scheme IRI.
        lang (str): The language. Defaults to "en".

    Returns:
        JSONResponse: The concepts.
    """
    return JSONResponse(
        content={
            "concepts": request.app.state.controller.get_concepts(
                concept_scheme_iri, lang=lang
            ),
        },
        media_type="application/json",
        status_code=HTTPStatus.OK,
    )


@router.get("/collection")
def get_collection(
    request: Request,
    collection_iri: str,
    lang: str = "en",
) -> CollectionResponse:
    """
    Returns a collection.
    Args:
        collection_iri (str): The collection IRI.
        lang (str): The language. Defaults to "en".
    Returns:
        JSONResponse: The collection.
    """
    return request.app.state.controller.get_collection(collection_iri, lang=lang)


@router.get("/concept")
def get_concept(
    request: Request, concept_iri: str, lang: str = "en"
) -> FullConeptResponse:
    """
    Returns a concept.

    Args:
        concept_iri (str): The concept IRI.
        lang (str): The language. Defaults to "en".

    Returns:
        FullConeptResponse: The concept with concept scheme and relations.
    """
    return request.app.state.controller.get_concept(concept_iri, lang=lang)