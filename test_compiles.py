from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB
import sqlalchemy

@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"
