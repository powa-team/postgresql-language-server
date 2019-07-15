from pygls.types import Range, Position, Diagnostic, DiagnosticSeverity
from pglast import Node

LINTERS = {}


class Linter:

    def __init__(self, code, name, fun):
        self.code = code
        self.name = name or fun.__name__
        self.fun = fun
        self.description = self.fun.__doc__

    def __call__(self, *args, **kwargs):
        return self.fun(*args, **kwargs)

    @property
    def severity(self):
        if self.code.startswith('W'):
            return DiagnosticSeverity.Warning
        if self.code.startswith('E'):
            return DiagnosticSeverity.Error
        if self.code.startswith('H'):
            return DiagnosticSeverity.Hint
        if self.code.startswith('I'):
            return DiagnosticSeverity.Information


class linter:

    def __init__(self, code, name=None):
        self.name = name
        self.code = code

    def __call__(self, fun):
        if self.code in LINTERS:
            raise KeyError('Linter %s already exists' % self.code)
        LINTERS[self.code] = linter = Linter(self.code, self.name, fun)
        return linter


class LinterContext:

    def __init__(self, search_path):
        self.search_path = search_path


def _make_diagnostic(linter, node, message):
    start_pos = Position(node.parse_tree.loc)
    end_pos = Position(node.parse_tree.loc + 1)
    return Diagnostic(
            Range(start_pos, end_pos),
            message=message,
            code=linter.code,
            severity=linter.severity)


def lint(statement, metadata, context):
    statement = Node(statement)
    for linter in LINTERS.values():
        yield from (_make_diagnostic(linter, node, message)
                    for node, message in linter(statement, metadata, context))


@linter('WDS0001')
def dml_missing_where_clause(statement, metadata, context):
    print(statement)
    if statement.node_tag in ('DeleteStmt', 'UpdateStmt'):
        if not statement.whereClause:
            yield statement, 'Missing WHERE clause in %s' % statement.node_tag
