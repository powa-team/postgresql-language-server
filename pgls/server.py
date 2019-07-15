import json
import traceback

from pygls.features import (COMPLETION, TEXT_DOCUMENT_DID_CHANGE,
                            TEXT_DOCUMENT_DID_CLOSE, TEXT_DOCUMENT_DID_OPEN,
                            TEXT_DOCUMENT_DID_SAVE)
from pygls.server import LanguageServer
from pygls.types import (CompletionItem, CompletionList, CompletionParams,
                         ConfigurationItem, ConfigurationParams, Diagnostic,
                         DiagnosticSeverity,
                         DidChangeTextDocumentParams,
                         DidCloseTextDocumentParams, DidOpenTextDocumentParams,
                         DidSaveTextDocumentParams,
                         Location,
                         MessageType, Position, Range, Registration,
                         RegistrationParams, Unregistration,
                         UnregistrationParams)
from pygls.protocol import LanguageServerProtocol, logger as protocollogger
from pglast import parse_sql
from pglast.parser import ParseError

from pgls.linter import lint


class PgLanguageServer(LanguageServer):
    pass


class JSONEncoder(json.JSONEncoder):

    def default(self, obj):
        return {key: value for key, value in obj.__dict__.items()
                if value is not None}


def char_pos_to_position(buf, position):
    seekpos = 0
    position = position - 1
    for lineno, line in enumerate(buf.split('\n')):
        if seekpos + (len(line) + 1) > position:
            return Position(lineno, position - seekpos)
        seekpos += len(line) + 1


class PgLanguageProtocol(LanguageServerProtocol):

    def _send_data(self, data):
        """Sends data to the client."""
        if not data:
            return

        try:
            body = json.dumps(data, cls=JSONEncoder)
            content_length = len(body.encode(self.CHARSET)) if body else 0

            response = (
                'Content-Length: {}\r\n'
                'Content-Type: {}; charset={}\r\n\r\n'
                '{}'.format(content_length,
                            self.CONTENT_TYPE,
                            self.CHARSET,
                            body)
            )

            protocollogger.info('Sending data: {}'.format(body))

            self.transport.write(response.encode(self.CHARSET))
        except Exception:
            protocollogger.error(traceback.format_exc())


pg_language_server = PgLanguageServer(protocol_cls=PgLanguageProtocol)


def _validate(ls, params):
    ls.show_message_log('Linting SQL...')
    text_doc = ls.workspace.get_document(params.textDocument.uri)
    source = text_doc.source
    diagnostics = _validate_sql(source, params.textDocument.uri)
    ls.publish_diagnostics(text_doc.uri, diagnostics)


def _validate_sql(sqlfile, uri):
    diagnostics = []
    try:
        statements = parse_sql(sqlfile)
    except ParseError as e:
        pos = char_pos_to_position(sqlfile, e.location)
        diagnostics.append(Diagnostic(Range(pos, pos),
                                      message=e.args[0],
                                      severity=DiagnosticSeverity.Error,
                                      source=type(pg_language_server).__name__))
        return diagnostics
    for statement in statements:
        for diag in lint(statement, None, None):
            diagnostics.append(diag)
    return diagnostics


@pg_language_server.feature(TEXT_DOCUMENT_DID_CHANGE)
def did_change(ls, params: DidChangeTextDocumentParams):
    """Text document did change notification."""
    _validate(ls, params)


@pg_language_server.feature(TEXT_DOCUMENT_DID_OPEN)
async def did_open(ls, params: DidOpenTextDocumentParams):
    """Text document did open notification."""
    ls.show_message('Open SQL FILE...')
    _validate(ls, params)


@pg_language_server.feature(TEXT_DOCUMENT_DID_SAVE)
async def did_save(ls, params: DidSaveTextDocumentParams):
    ls.show_message('Saving SQL FILE...')
    _validate(ls, params)
