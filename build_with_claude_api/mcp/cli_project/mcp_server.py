from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts import base
from pydantic import Field

mcp = FastMCP("DocumentMCP", log_level="ERROR")


docs = {
    "deposition.md": "This deposition covers the testimony of Angela Smith, P.E.",
    "report.pdf": "The report details the state of a 20m condenser tower.",
    "financials.docx": "These financials outline the project's budget and expenditures.",
    "outlook.pdf": "This document presents the projected future performance of the system.",
    "plan.md": "The plan outlines the steps for the project's implementation.",
    "spec.txt": "These specifications define the technical requirements for the equipment.",
}

@mcp.tool(
    name="read_doc_contents",
    description="Read the contents of a document and return it as a string"
)
def read_doc_contents(
    doc_id:str = Field(description="id of the document to read")
):
    if doc_id not in docs:
        raise ValueError(f'Document with id {doc_id} not found')
    return docs[doc_id]


@mcp.tool(
    name="edit_document",
    description="Edit a document by replacing a string in the documents content with a new string."
)
def edit_document(
    doc_id:str = Field(description="id of the document to edit"),
    old_text:str = Field(description="old text present in the document that will be replaced"),
    new_text:str = Field(description="new text that will be added to the document")
):
    if doc_id not in docs:
        raise ValueError(f'Document with id {doc_id} not found')
    docs[doc_id] = docs[doc_id].replace(old_text, new_text)
    return "Successfully editted document"


@mcp.resource(
    "docs://documents",
    mime_type="application/json"
)
def list_docs() -> list[str]:
    return list(docs.keys())


@mcp.resource(
    "docs://documents/{doc_id}",
    mime_type="text/plain"
)
def read_doc(doc_id: str):
    if doc_id not in docs:
        raise ValueError(f'Document with id {doc_id} not found')
    return docs[doc_id]


@mcp.prompt(
    name = "format",
    description = "Formats a document using markdown syntax"
)
def format_document(doc_id:str = Field(description="The document id to format as markdown")) -> list[base.Message]:
    prompt = f"""
Your goal is to reformat a document to be written with markdown syntax.

The id of the document you need to reformat is:

{doc_id}


Add in headers, bullet points, tables, etc as necessary. Feel free to add in extra formatting.
Use the 'edit_document' tool to edit the document. After the document has been reformatted...
"""
    return [base.UserMessage(prompt)]

# TODO: Write a prompt to summarize a doc


if __name__ == "__main__":
    mcp.run(transport="stdio")
