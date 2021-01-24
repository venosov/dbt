import pickle
import pytest

from dbt.node_types import NodeType
from dbt.contracts.files import FileHash
from dbt.contracts.graph.model_config import (
    NodeConfig,
    SeedConfig,
    TestConfig,
    SnapshotConfig,
    SourceConfig,
    EmptySnapshotConfig,
    Hook,
)
from dbt.contracts.graph.parsed import (
    ParsedModelNode,
    DependsOn,
    ColumnInfo,
    ParsedSchemaTestNode,
    ParsedSnapshotNode,
    IntermediateSnapshotNode,
    ParsedNodePatch,
    ParsedMacro,
    ParsedExposure,
    ParsedSeedNode,
    Docs,
    MacroDependsOn,
    ParsedSourceDefinition,
    ParsedDocumentation,
    ParsedHookNode,
    ExposureOwner,
    TestMetadata,
)
from dbt.contracts.graph.unparsed import (
    ExposureType,
    FreshnessThreshold,
    MaturityType,
    Quoting,
    Time,
    TimePeriod,
)
from dbt import flags

from dbt.dataclass_schema import ValidationError
from .utils import ContractTestCase, assert_symmetric, assert_from_dict, assert_to_dict, compare_dicts, assert_fails_validation, dict_replace, replace_config


@pytest.fixture(autouse=True)
def strict_mode():
    flags.STRICT_MODE = True
    yield
    flags.STRICT_MODE = False


@pytest.fixture
def populated_node_config_object():
    result = NodeConfig(
        column_types={'a': 'text'},
        materialized='table',
        post_hook=[Hook(sql='insert into blah(a, b) select "1", 1')]
    )
    result._extra['extra'] = 'even more'
    return result


@pytest.fixture
def populated_node_config_dict():
    return {
        'column_types': {'a': 'text'},
        'enabled': True,
        'materialized': 'table',
        'persist_docs': {},
        'post-hook': [{'sql': 'insert into blah(a, b) select "1", 1', 'transaction': True}],
        'pre-hook': [],
        'quoting': {},
        'tags': [],
        'vars': {},
        'extra': 'even more',
    }


def test_config_populated(populated_node_config_object, populated_node_config_dict):
    assert_symmetric(populated_node_config_object, populated_node_config_dict, NodeConfig)
    pickle.loads(pickle.dumps(populated_node_config_object))


@pytest.fixture
def unrendered_node_config_dict():
    return {
        'column_types': {'a': 'text'},
        'materialized': 'table',
        'post_hook': 'insert into blah(a, b) select "1", 1',
    }


different_node_configs = [
    lambda c: dict_replace(c, post_hook=[]),
    lambda c: dict_replace(c, materialized='view'),
    lambda c: dict_replace(c, quoting={'database': True}),
    lambda c: dict_replace(c, extra='different extra'),
    lambda c: dict_replace(c, column_types={'a': 'varchar(256)'}),
]


same_node_configs = [
    lambda c: dict_replace(c, tags=['mytag']),
    lambda c: dict_replace(c, alias='changed'),
    lambda c: dict_replace(c, schema='changed'),
    lambda c: dict_replace(c, database='changed'),
]


@pytest.mark.parametrize('func', different_node_configs)
def test_config_different(unrendered_node_config_dict, func):
    value = func(unrendered_node_config_dict)
    assert not NodeConfig.same_contents(unrendered_node_config_dict, value)


@pytest.mark.parametrize('func', same_node_configs)
def test_config_same(unrendered_node_config_dict, func):
    value = func(unrendered_node_config_dict)
    assert unrendered_node_config_dict != value
    assert NodeConfig.same_contents(unrendered_node_config_dict, value)


@pytest.fixture
def base_parsed_model_dict():
    return {
        'name': 'foo',
        'root_path': '/root/',
        'resource_type': str(NodeType.Model),
        'path': '/root/x/path.sql',
        'original_file_path': '/root/path.sql',
        'package_name': 'test',
        'raw_sql': 'select * from wherever',
        'unique_id': 'model.test.foo',
        'fqn': ['test', 'models', 'foo'],
        'refs': [],
        'sources': [],
        'depends_on': {'macros': [], 'nodes': []},
        'database': 'test_db',
        'description': '',
        'schema': 'test_schema',
        'alias': 'bar',
        'tags': [],
        'config': {
            'column_types': {},
            'enabled': True,
            'materialized': 'view',
            'persist_docs': {},
            'post-hook': [],
            'pre-hook': [],
            'quoting': {},
            'tags': [],
            'vars': {},
        },
        'deferred': False,
        'docs': {'show': True},
        'columns': {},
        'meta': {},
        'checksum': {'name': 'sha256', 'checksum': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'},
        'unrendered_config': {},
    }


@pytest.fixture
def basic_parsed_model_object():
    return ParsedModelNode(
        package_name='test',
        root_path='/root/',
        path='/root/x/path.sql',
        original_file_path='/root/path.sql',
        raw_sql='select * from wherever',
        name='foo',
        resource_type=NodeType.Model,
        unique_id='model.test.foo',
        fqn=['test', 'models', 'foo'],
        refs=[],
        sources=[],
        depends_on=DependsOn(),
        description='',
        database='test_db',
        schema='test_schema',
        alias='bar',
        tags=[],
        config=NodeConfig(),
        meta={},
        checksum=FileHash.from_contents(''),
    )


@pytest.fixture
def minimal_parsed_model_dict():
    return {
        'name': 'foo',
        'root_path': '/root/',
        'resource_type': str(NodeType.Model),
        'path': '/root/x/path.sql',
        'original_file_path': '/root/path.sql',
        'package_name': 'test',
        'raw_sql': 'select * from wherever',
        'unique_id': 'model.test.foo',
        'fqn': ['test', 'models', 'foo'],
        'database': 'test_db',
        'schema': 'test_schema',
        'alias': 'bar',
        'checksum': {'name': 'sha256', 'checksum': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'},
        'unrendered_config': {},
    }


@pytest.fixture
def complex_parsed_model_dict():
    return {
        'name': 'foo',
        'root_path': '/root/',
        'resource_type': str(NodeType.Model),
        'path': '/root/x/path.sql',
        'original_file_path': '/root/path.sql',
        'package_name': 'test',
        'raw_sql': 'select * from {{ ref("bar") }}',
        'unique_id': 'model.test.foo',
        'fqn': ['test', 'models', 'foo'],
        'refs': [],
        'sources': [],
        'depends_on': {'macros': [], 'nodes': ['model.test.bar']},
        'database': 'test_db',
        'deferred': True,
        'description': 'My parsed node',
        'schema': 'test_schema',
        'alias': 'bar',
        'tags': ['tag'],
        'meta': {},
        'config': {
            'column_types': {'a': 'text'},
            'enabled': True,
            'materialized': 'ephemeral',
            'persist_docs': {},
            'post-hook': [{'sql': 'insert into blah(a, b) select "1", 1', 'transaction': True}],
            'pre-hook': [],
            'quoting': {},
            'tags': [],
            'vars': {'foo': 100},
        },
        'docs': {'show': True},
        'columns': {
            'a': {
                'name': 'a',
                'description': 'a text field',
                'meta': {},
                'tags': [],
            },
        },
        'checksum': {'name': 'sha256', 'checksum': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'},
        'unrendered_config': {
            'column_types': {'a': 'text'},
            'materialized': 'ephemeral',
            'post_hook': ['insert into blah(a, b) select "1", 1'],
            'vars': {'foo': 100},
        },
    }


@pytest.fixture
def complex_parsed_model_object():
    return ParsedModelNode(
        package_name='test',
        root_path='/root/',
        path='/root/x/path.sql',
        original_file_path='/root/path.sql',
        raw_sql='select * from {{ ref("bar") }}',
        name='foo',
        resource_type=NodeType.Model,
        unique_id='model.test.foo',
        fqn=['test', 'models', 'foo'],
        refs=[],
        sources=[],
        depends_on=DependsOn(nodes=['model.test.bar']),
        deferred=True,
        description='My parsed node',
        database='test_db',
        schema='test_schema',
        alias='bar',
        tags=['tag'],
        meta={},
        config=NodeConfig(
            column_types={'a': 'text'},
            materialized='ephemeral',
            post_hook=[Hook(sql='insert into blah(a, b) select "1", 1')],
            vars={'foo': 100},
        ),
        columns={'a': ColumnInfo('a', 'a text field', {})},
        checksum=FileHash.from_contents(''),
        unrendered_config={
            'column_types': {'a': 'text'},
            'materialized': 'ephemeral',
            'post_hook': ['insert into blah(a, b) select "1", 1'],
            'vars': {'foo': 100},
        },
    )


def test_model_basic(basic_parsed_model_object, base_parsed_model_dict, minimal_parsed_model_dict):
    node = basic_parsed_model_object
    node_dict = base_parsed_model_dict
    assert_symmetric(node, node_dict)
    assert node.empty is False
    assert node.is_refable is True
    assert node.is_ephemeral is False
    assert node.local_vars() == {}

    minimum = minimal_parsed_model_dict
    assert_from_dict(node, minimum)
    pickle.loads(pickle.dumps(node))


def test_model_complex(complex_parsed_model_object, complex_parsed_model_dict):
    node = complex_parsed_model_object
    node_dict = complex_parsed_model_dict
    assert_symmetric(node, node_dict)
    assert node.empty is False
    assert node.is_refable is True
    assert node.is_ephemeral is True
    assert node.local_vars() == {'foo': 100}


def test_invalid_bad_tags(base_parsed_model_dict):
    # bad top-level field
    bad_tags = base_parsed_model_dict
    bad_tags['tags'] = 100
    assert_fails_validation(bad_tags, ParsedModelNode)


def test_invalid_bad_materialized(base_parsed_model_dict):
    # bad nested field
    bad_materialized = base_parsed_model_dict
    bad_materialized['config']['materialized'] = None
    assert_fails_validation(bad_materialized, ParsedModelNode)


unchanged_nodes = [
    lambda u: (u, u.replace(tags=['mytag'])),
    lambda u: (u, u.replace(meta={'something': 1000})),
    # True -> True
    lambda u: (
        replace_config(u, persist_docs={'relation': True}),
        replace_config(u, persist_docs={'relation': True}),
    ),
    lambda u: (
        replace_config(u, persist_docs={'columns': True}),
        replace_config(u, persist_docs={'columns': True}),
    ),
    # only columns docs enabled, but description changed
    lambda u: (
        replace_config(u, persist_docs={'columns': True}),
        replace_config(u, persist_docs={'columns': True}).replace(description='a model description'),
    ),
    # only relation docs eanbled, but columns changed
    lambda u: (
        replace_config(u, persist_docs={'relation': True}),
        replace_config(u, persist_docs={'relation': True}).replace(columns={'a': ColumnInfo(name='a', description='a column description')}),
    ),

    # not tracked, we track config.alias/config.schema/config.database
    lambda u: (u, u.replace(alias='other')),
    lambda u: (u, u.replace(schema='other')),
    lambda u: (u, u.replace(database='other')),
]


changed_nodes = [
    lambda u: (u, u.replace(fqn=['test', 'models', 'subdir', 'foo'], original_file_path='models/subdir/foo.sql', path='/root/models/subdir/foo.sql')),

    # None -> False is a config change even though it's pretty much the same
    lambda u: (u, replace_config(u, persist_docs={'relation': False})),
    lambda u: (u, replace_config(u, persist_docs={'columns': False})),

    # persist docs was true for the relation and we changed the model description
    lambda u: (
        replace_config(u, persist_docs={'relation': True}),
        replace_config(u, persist_docs={'relation': True}).replace(description='a model description'),
    ),
    # persist docs was true for columns and we changed the model description
    lambda u: (
        replace_config(u, persist_docs={'columns': True}),
        replace_config(u, persist_docs={'columns': True}).replace(columns={'a': ColumnInfo(name='a', description='a column description')}),
    ),

    # not tracked, we track config.alias/config.schema/config.database
    lambda u: (u, replace_config(u, alias='other')),
    lambda u: (u, replace_config(u, schema='other')),
    lambda u: (u, replace_config(u, database='other')),
]


@pytest.mark.parametrize('func', unchanged_nodes)
def test_compare_unchanged_parsed_model(func, basic_parsed_model_object):
    node, compare = func(basic_parsed_model_object)
    assert node.same_contents(compare)


@pytest.mark.parametrize('func', changed_nodes)
def test_compare_changed_model(func, basic_parsed_model_object):
    node, compare = func(basic_parsed_model_object)
    assert not node.same_contents(compare)


@pytest.fixture
def basic_parsed_seed_dict():
    return {
        'name': 'foo',
        'root_path': '/root/',
        'resource_type': str(NodeType.Seed),
        'path': '/root/seeds/seed.csv',
        'original_file_path': 'seeds/seed.csv',
        'package_name': 'test',
        'raw_sql': '',
        'unique_id': 'seed.test.foo',
        'fqn': ['test', 'seeds', 'foo'],
        'refs': [],
        'sources': [],
        'depends_on': {'macros': [], 'nodes': []},
        'database': 'test_db',
        'description': '',
        'schema': 'test_schema',
        'tags': [],
        'alias': 'foo',
        'config': {
            'column_types': {},
            'enabled': True,
            'materialized': 'seed',
            'persist_docs': {},
            'post-hook': [],
            'pre-hook': [],
            'quoting': {},
            'tags': [],
            'vars': {},
        },
        'deferred': False,
        'docs': {'show': True},
        'columns': {},
        'meta': {},
        'checksum': {'name': 'path', 'checksum': 'seeds/seed.csv'},
        'unrendered_config': {},
    }


@pytest.fixture
def basic_parsed_seed_object():
    return ParsedSeedNode(
        name='foo',
        root_path='/root/',
        resource_type=NodeType.Seed,
        path='/root/seeds/seed.csv',
        original_file_path='seeds/seed.csv',
        package_name='test',
        raw_sql='',
        unique_id='seed.test.foo',
        fqn=['test', 'seeds', 'foo'],
        refs=[],
        sources=[],
        depends_on=DependsOn(),
        database='test_db',
        description='',
        schema='test_schema',
        tags=[],
        alias='foo',
        config=SeedConfig(),
        # config=SeedConfig(quote_columns=True),
        deferred=False,
        docs=Docs(show=True),
        columns={},
        meta={},
        checksum=FileHash(name='path', checksum='seeds/seed.csv'),
        unrendered_config={},
    )


@pytest.fixture
def minimal_parsed_seed_dict():
    return {
        'name': 'foo',
        'root_path': '/root/',
        'resource_type': str(NodeType.Seed),
        'path': '/root/seeds/seed.csv',
        'original_file_path': 'seeds/seed.csv',
        'package_name': 'test',
        'raw_sql': '',
        'unique_id': 'seed.test.foo',
        'fqn': ['test', 'seeds', 'foo'],
        'database': 'test_db',
        'schema': 'test_schema',
        'alias': 'foo',
        'checksum': {'name': 'path', 'checksum': 'seeds/seed.csv'},
    }


@pytest.fixture
def complex_parsed_seed_dict():
    return {
        'name': 'foo',
        'root_path': '/root/',
        'resource_type': str(NodeType.Seed),
        'path': '/root/seeds/seed.csv',
        'original_file_path': 'seeds/seed.csv',
        'package_name': 'test',
        'raw_sql': '',
        'unique_id': 'seed.test.foo',
        'fqn': ['test', 'seeds', 'foo'],
        'refs': [],
        'sources': [],
        'depends_on': {'macros': [], 'nodes': []},
        'database': 'test_db',
        'description': 'a description',
        'schema': 'test_schema',
        'tags': ['mytag'],
        'alias': 'foo',
        'config': {
            'column_types': {},
            'enabled': True,
            'materialized': 'seed',
            'persist_docs': {'relation': True, 'columns': True},
            'post-hook': [],
            'pre-hook': [],
            'quoting': {},
            'tags': [],
            'vars': {},
            'quote_columns': True,
        },
        'deferred': False,
        'docs': {'show': True},
        'columns': {'a': {'name': 'a', 'description': 'a column description', 'meta': {}, 'tags': []}},
        'meta': {'foo': 1000},
        'checksum': {'name': 'sha256', 'checksum': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'},
        'unrendered_config': {
            'persist_docs': {'relation': True, 'columns': True},
        },
    }


@pytest.fixture
def complex_parsed_seed_object():
    return ParsedSeedNode(
        name='foo',
        root_path='/root/',
        resource_type=NodeType.Seed,
        path='/root/seeds/seed.csv',
        original_file_path='seeds/seed.csv',
        package_name='test',
        raw_sql='',
        unique_id='seed.test.foo',
        fqn=['test', 'seeds', 'foo'],
        refs=[],
        sources=[],
        depends_on=DependsOn(),
        database='test_db',
        description='a description',
        schema='test_schema',
        tags=['mytag'],
        alias='foo',
        config=SeedConfig(
            quote_columns=True,
            persist_docs={'relation': True, 'columns': True},
        ),
        deferred=False,
        docs=Docs(show=True),
        columns={'a': ColumnInfo(name='a', description='a column description')},
        meta={'foo': 1000},
        checksum=FileHash.from_contents(''),
        unrendered_config={
            'persist_docs': {'relation': True, 'columns': True},
        },
    )


def test_seed_basic(basic_parsed_seed_dict, basic_parsed_seed_object, minimal_parsed_seed_dict):
    assert_symmetric(basic_parsed_seed_object, basic_parsed_seed_dict)
    assert basic_parsed_seed_object.get_materialization() == 'seed'

    assert_from_dict(basic_parsed_seed_object, minimal_parsed_seed_dict, ParsedSeedNode)


def test_seed_complex(complex_parsed_seed_dict, complex_parsed_seed_object):
    assert_symmetric(complex_parsed_seed_object, complex_parsed_seed_dict)
    assert complex_parsed_seed_object.get_materialization() == 'seed'


unchanged_seeds = [
    lambda u: (u, u.replace(tags=['mytag'])),
    lambda u: (u, u.replace(meta={'something': 1000})),
    # True -> True
    lambda u: (
        replace_config(u, persist_docs={'relation': True}),
        replace_config(u, persist_docs={'relation': True}),
    ),
    lambda u: (
        replace_config(u, persist_docs={'columns': True}),
        replace_config(u, persist_docs={'columns': True}),
    ),
    # only columns docs enabled, but description changed
    lambda u: (
        replace_config(u, persist_docs={'columns': True}),
        replace_config(u, persist_docs={'columns': True}).replace(description='a model description'),
    ),
    # only relation docs eanbled, but columns changed
    lambda u: (
        replace_config(u, persist_docs={'relation': True}),
        replace_config(u, persist_docs={'relation': True}).replace(columns={'a': ColumnInfo(name='a', description='a column description')}),
    ),

    lambda u: (u, u.replace(alias='other')),
    lambda u: (u, u.replace(schema='other')),
    lambda u: (u, u.replace(database='other')),
]


changed_seeds = [
    lambda u: (u, u.replace(fqn=['test', 'models', 'subdir', 'foo'], original_file_path='models/subdir/foo.sql', path='/root/models/subdir/foo.sql')),

    # None -> False is a config change even though it's pretty much the same
    lambda u: (u, replace_config(u, persist_docs={'relation': False})),
    lambda u: (u, replace_config(u, persist_docs={'columns': False})),

    # persist docs was true for the relation and we changed the model description
    lambda u: (
        replace_config(u, persist_docs={'relation': True}),
        replace_config(u, persist_docs={'relation': True}).replace(description='a model description'),
    ),
    # persist docs was true for columns and we changed the model description
    lambda u: (
        replace_config(u, persist_docs={'columns': True}),
        replace_config(u, persist_docs={'columns': True}).replace(columns={'a': ColumnInfo(name='a', description='a column description')}),
    ),
    lambda u: (u, replace_config(u, alias='other')),
    lambda u: (u, replace_config(u, schema='other')),
    lambda u: (u, replace_config(u, database='other')),
]


@pytest.mark.parametrize('func', unchanged_seeds)
def test_compare_unchanged_parsed_seed(func, basic_parsed_seed_object):
    node, compare = func(basic_parsed_seed_object)
    assert node.same_contents(compare)


@pytest.mark.parametrize('func', changed_seeds)
def test_compare_changed_seed(func, basic_parsed_seed_object):
    node, compare = func(basic_parsed_seed_object)
    assert not node.same_contents(compare)


@pytest.fixture
def basic_parsed_model_patch_dict():
    return {
        'name': 'foo',
        'description': 'The foo model',
        'original_file_path': '/path/to/schema.yml',
        'docs': {'show': True},
        'meta': {},
        'yaml_key': 'models',
        'package_name': 'test',
        'columns': {
            'a': {
                'name': 'a',
                'description': 'a text field',
                'meta': {},
                'tags': [],
            },
        },
    }


@pytest.fixture
def basic_parsed_model_patch_object():
    return ParsedNodePatch(
        name='foo',
        yaml_key='models',
        package_name='test',
        description='The foo model',
        original_file_path='/path/to/schema.yml',
        columns={'a': ColumnInfo(name='a', description='a text field', meta={})},
        docs=Docs(),
        meta={},
    )


@pytest.fixture
def patched_model_object():
    return ParsedModelNode(
        package_name='test',
        root_path='/root/',
        path='/root/x/path.sql',
        original_file_path='/root/path.sql',
        raw_sql='select * from wherever',
        name='foo',
        resource_type=NodeType.Model,
        unique_id='model.test.foo',
        fqn=['test', 'models', 'foo'],
        refs=[],
        sources=[],
        depends_on=DependsOn(),
        description='The foo model',
        database='test_db',
        schema='test_schema',
        alias='bar',
        tags=[],
        meta={},
        config=NodeConfig(),
        patch_path='/path/to/schema.yml',
        columns={'a': ColumnInfo(name='a', description='a text field', meta={})},
        docs=Docs(),
        checksum=FileHash.from_contents(''),
        unrendered_config={},
    )


def test_patch_parsed_model(basic_parsed_model_object, basic_parsed_model_patch_object, patched_model_object):
    pre_patch = basic_parsed_model_object
    pre_patch.patch(basic_parsed_model_patch_object)
    assert patched_model_object == pre_patch


def test_patch_parsed_model_invalid(basic_parsed_model_object, basic_parsed_model_patch_object):
    pre_patch = basic_parsed_model_object # ParsedModelNode
    patch = basic_parsed_model_patch_object.replace(description=None)
    with pytest.raises(ValidationError):
        pre_patch.patch(patch)


@pytest.fixture
def minimal_parsed_hook_dict():
    return {
        'name': 'foo',
        'root_path': '/root/',
        'resource_type': str(NodeType.Operation),
        'path': '/root/x/path.sql',
        'original_file_path': '/root/path.sql',
        'package_name': 'test',
        'raw_sql': 'select * from wherever',
        'unique_id': 'model.test.foo',
        'fqn': ['test', 'models', 'foo'],
        'database': 'test_db',
        'schema': 'test_schema',
        'alias': 'bar',
        'checksum': {'name': 'sha256', 'checksum': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'},
    }


@pytest.fixture
def base_parsed_hook_dict():
    return {
        'name': 'foo',
        'root_path': '/root/',
        'resource_type': str(NodeType.Operation),
        'path': '/root/x/path.sql',
        'original_file_path': '/root/path.sql',
        'package_name': 'test',
        'raw_sql': 'select * from wherever',
        'unique_id': 'model.test.foo',
        'fqn': ['test', 'models', 'foo'],
        'refs': [],
        'sources': [],
        'depends_on': {'macros': [], 'nodes': []},
        'database': 'test_db',
        'deferred': False,
        'description': '',
        'schema': 'test_schema',
        'alias': 'bar',
        'tags': [],
        'config': {
            'column_types': {},
            'enabled': True,
            'materialized': 'view',
            'persist_docs': {},
            'post-hook': [],
            'pre-hook': [],
            'quoting': {},
            'tags': [],
            'vars': {},
        },
        'docs': {'show': True},
        'columns': {},
        'meta': {},
        'checksum': {'name': 'sha256', 'checksum': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'},
        'unrendered_config': {},
    }


@pytest.fixture
def base_parsed_hook_object():
    return ParsedHookNode(
        package_name='test',
        root_path='/root/',
        path='/root/x/path.sql',
        original_file_path='/root/path.sql',
        raw_sql='select * from wherever',
        name='foo',
        resource_type=NodeType.Operation,
        unique_id='model.test.foo',
        fqn=['test', 'models', 'foo'],
        refs=[],
        sources=[],
        depends_on=DependsOn(),
        description='',
        deferred=False,
        database='test_db',
        schema='test_schema',
        alias='bar',
        tags=[],
        config=NodeConfig(),
        index=None,
        checksum=FileHash.from_contents(''),
        unrendered_config={},
    )


@pytest.fixture
def complex_parsed_hook_dict():
    return {
        'name': 'foo',
        'root_path': '/root/',
        'resource_type': str(NodeType.Operation),
        'path': '/root/x/path.sql',
        'original_file_path': '/root/path.sql',
        'package_name': 'test',
        'raw_sql': 'select * from {{ ref("bar") }}',
        'unique_id': 'model.test.foo',
        'fqn': ['test', 'models', 'foo'],
        'refs': [],
        'sources': [],
        'depends_on': {'macros': [], 'nodes': ['model.test.bar']},
        'deferred': False,
        'database': 'test_db',
        'description': 'My parsed node',
        'schema': 'test_schema',
        'alias': 'bar',
        'tags': ['tag'],
        'meta': {},
        'config': {
            'column_types': {'a': 'text'},
            'enabled': True,
            'materialized': 'table',
            'persist_docs': {},
            'post-hook': [],
            'pre-hook': [],
            'quoting': {},
            'tags': [],
            'vars': {},
        },
        'docs': {'show': True},
        'columns': {
            'a': {
                'name': 'a',
                'description': 'a text field',
                'meta': {},
                'tags': [],
            },
        },
        'index': 13,
        'checksum': {'name': 'sha256', 'checksum': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'},
        'unrendered_config': {
            'column_types': {'a': 'text'},
            'materialized': 'table',
        },
    }


@pytest.fixture
def complex_parsed_hook_object():
    return ParsedHookNode(
        package_name='test',
        root_path='/root/',
        path='/root/x/path.sql',
        original_file_path='/root/path.sql',
        raw_sql='select * from {{ ref("bar") }}',
        name='foo',
        resource_type=NodeType.Operation,
        unique_id='model.test.foo',
        fqn=['test', 'models', 'foo'],
        refs=[],
        sources=[],
        depends_on=DependsOn(nodes=['model.test.bar']),
        description='My parsed node',
        deferred=False,
        database='test_db',
        schema='test_schema',
        alias='bar',
        tags=['tag'],
        meta={},
        config=NodeConfig(
            column_types={'a': 'text'},
            materialized='table',
            post_hook=[]
        ),
        columns={'a': ColumnInfo('a', 'a text field', {})},
        index=13,
        checksum=FileHash.from_contents(''),
        unrendered_config={
            'column_types': {'a': 'text'},
            'materialized': 'table',
        },
    )


def test_basic_parsed_hook(minimal_parsed_hook_dict, base_parsed_hook_dict, base_parsed_hook_object):
    node = base_parsed_hook_object
    node_dict = base_parsed_hook_dict
    minimum = minimal_parsed_hook_dict

    assert_symmetric(node, node_dict, ParsedHookNode)
    assert node.empty is False
    assert node.is_refable is False
    assert node.get_materialization() == 'view'
    assert_from_dict(node, minimum, ParsedHookNode)
    pickle.loads(pickle.dumps(node))


def test_complex_parsed_hook(complex_parsed_hook_dict, complex_parsed_hook_object):
    node = complex_parsed_hook_object
    node_dict = complex_parsed_hook_dict
    assert_symmetric(node, node_dict)
    assert node.empty is False
    assert node.is_refable is False
    assert node.get_materialization() == 'table'


def test_invalid_hook_index_type(base_parsed_hook_dict):
    bad_index = base_parsed_hook_dict
    bad_index['index'] = 'a string!?'
    assert_fails_validation(bad_index, ParsedHookNode)


@pytest.fixture
def minimal_parsed_schema_test_dict():
    return {
        'name': 'foo',
        'root_path': '/root/',
        'resource_type': str(NodeType.Test),
        'path': '/root/x/path.sql',
        'original_file_path': '/root/path.sql',
        'package_name': 'test',
        'raw_sql': 'select * from wherever',
        'unique_id': 'test.test.foo',
        'fqn': ['test', 'models', 'foo'],
        'database': 'test_db',
        'schema': 'test_schema',
        'alias': 'bar',
        'meta': {},
        'test_metadata': {
            'name': 'foo',
            'kwargs': {},
        },
        'checksum': {'name': 'sha256', 'checksum': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'},
    }


@pytest.fixture
def basic_parsed_schema_test_dict():
    return {
        'name': 'foo',
        'root_path': '/root/',
        'resource_type': str(NodeType.Test),
        'path': '/root/x/path.sql',
        'original_file_path': '/root/path.sql',
        'package_name': 'test',
        'raw_sql': 'select * from wherever',
        'unique_id': 'test.test.foo',
        'fqn': ['test', 'models', 'foo'],
        'refs': [],
        'sources': [],
        'depends_on': {'macros': [], 'nodes': []},
        'deferred': False,
        'database': 'test_db',
        'description': '',
        'schema': 'test_schema',
        'alias': 'bar',
        'tags': [],
        'meta': {},
        'config': {
            'column_types': {},
            'enabled': True,
            'materialized': 'test',
            'persist_docs': {},
            'post-hook': [],
            'pre-hook': [],
            'quoting': {},
            'tags': [],
            'vars': {},
            'severity': 'ERROR',
        },
        'docs': {'show': True},
        'columns': {},
        'test_metadata': {
            'name': 'foo',
            'kwargs': {},
        },
        'checksum': {'name': 'sha256', 'checksum': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'},
        'unrendered_config': {},
    }


@pytest.fixture
def basic_parsed_schema_test_object():
    return ParsedSchemaTestNode(
        package_name='test',
        root_path='/root/',
        path='/root/x/path.sql',
        original_file_path='/root/path.sql',
        raw_sql='select * from wherever',
        name='foo',
        resource_type=NodeType.Test,
        unique_id='test.test.foo',
        fqn=['test', 'models', 'foo'],
        refs=[],
        sources=[],
        depends_on=DependsOn(),
        description='',
        database='test_db',
        schema='test_schema',
        alias='bar',
        tags=[],
        meta={},
        config=TestConfig(),
        test_metadata=TestMetadata(namespace=None, name='foo', kwargs={}),
        checksum=FileHash.from_contents(''),
    )


@pytest.fixture
def complex_parsed_schema_test_dict():
    return {
        'name': 'foo',
        'root_path': '/root/',
        'resource_type': str(NodeType.Test),
        'path': '/root/x/path.sql',
        'original_file_path': '/root/path.sql',
        'package_name': 'test',
        'raw_sql': 'select * from {{ ref("bar") }}',
        'unique_id': 'test.test.foo',
        'fqn': ['test', 'models', 'foo'],
        'refs': [],
        'sources': [],
        'depends_on': {'macros': [], 'nodes': ['model.test.bar']},
        'database': 'test_db',
        'deferred': False,
        'description': 'My parsed node',
        'schema': 'test_schema',
        'alias': 'bar',
        'tags': ['tag'],
        'meta': {},
        'config': {
            'column_types': {'a': 'text'},
            'enabled': True,
            'materialized': 'table',
            'persist_docs': {},
            'post-hook': [],
            'pre-hook': [],
            'quoting': {},
            'tags': [],
            'vars': {},
            'severity': 'WARN',
            'extra_key': 'extra value'
        },
        'docs': {'show': False},
        'columns': {
            'a': {
                'name': 'a',
                'description': 'a text field',
                'meta': {},
                'tags': [],
            },
        },
        'column_name': 'id',
        'test_metadata': {
            'name': 'foo',
            'kwargs': {},
        },
        'checksum': {'name': 'sha256', 'checksum': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'},
        'unrendered_config': {
            'column_types': {'a': 'text'},
            'materialized': 'table',
            'severity': 'WARN'
        },
    }


@pytest.fixture
def complex_parsed_schema_test_object():
    cfg = TestConfig(
        column_types={'a': 'text'},
        materialized='table',
        severity='WARN'
    )
    cfg._extra.update({'extra_key': 'extra value'})
    return ParsedSchemaTestNode(
        package_name='test',
        root_path='/root/',
        path='/root/x/path.sql',
        original_file_path='/root/path.sql',
        raw_sql='select * from {{ ref("bar") }}',
        name='foo',
        resource_type=NodeType.Test,
        unique_id='test.test.foo',
        fqn=['test', 'models', 'foo'],
        refs=[],
        sources=[],
        depends_on=DependsOn(nodes=['model.test.bar']),
        description='My parsed node',
        database='test_db',
        schema='test_schema',
        alias='bar',
        tags=['tag'],
        meta={},
        config=cfg,
        columns={'a': ColumnInfo('a', 'a text field',{})},
        column_name='id',
        docs=Docs(show=False),
        test_metadata=TestMetadata(namespace=None, name='foo', kwargs={}),
        checksum=FileHash.from_contents(''),
        unrendered_config={
            'column_types': {'a': 'text'},
            'materialized': 'table',
            'severity': 'WARN'
        },
    )


def test_basic_schema_test_node(minimal_parsed_schema_test_dict, basic_parsed_schema_test_dict, basic_parsed_schema_test_object):
    node = basic_parsed_schema_test_object
    node_dict = basic_parsed_schema_test_dict
    minimum = minimal_parsed_schema_test_dict
    assert_symmetric(node, node_dict, ParsedSchemaTestNode)

    assert node.empty is False
    assert node.is_ephemeral is False
    assert node.is_refable is False
    assert node.get_materialization() == 'test'

    assert_from_dict(node, minimum, ParsedSchemaTestNode)
    pickle.loads(pickle.dumps(node))


def test_complex_schema_test_node(complex_parsed_schema_test_dict, complex_parsed_schema_test_object):
    # this tests for the presence of _extra keys
    node = complex_parsed_schema_test_object  # ParsedSchemaTestNode
    assert(node.config._extra['extra_key'])
    node_dict = complex_parsed_schema_test_dict
    assert_symmetric(node, node_dict)
    assert node.empty is False


def test_invalid_column_name_type(complex_parsed_schema_test_dict):
    # bad top-level field
    bad_column_name = complex_parsed_schema_test_dict
    bad_column_name['column_name'] = {}
    assert_fails_validation(bad_column_name, ParsedSchemaTestNode)


def test_invalid_severity(complex_parsed_schema_test_dict):
    invalid_config_value = complex_parsed_schema_test_dict
    invalid_config_value['config']['severity'] = 'WERROR'
    assert_fails_validation(invalid_config_value, ParsedSchemaTestNode)


@pytest.fixture
def basic_timestamp_snapshot_config_dict():
    return {
        'column_types': {},
        'enabled': True,
        'materialized': 'snapshot',
        'persist_docs': {},
        'post-hook': [],
        'pre-hook': [],
        'quoting': {},
        'tags': [],
        'vars': {},
        'unique_key': 'id',
        'strategy': 'timestamp',
        'updated_at': 'last_update',
        'target_database': 'some_snapshot_db',
        'target_schema': 'some_snapshot_schema',
    }


@pytest.fixture
def basic_timestamp_snapshot_config_object():
    return SnapshotConfig(
        strategy='timestamp',
        updated_at='last_update',
        unique_key='id',
        target_database='some_snapshot_db',
        target_schema='some_snapshot_schema',
    )


@pytest.fixture
def complex_timestamp_snapshot_config_dict():
    return {
        'column_types': {'a': 'text'},
        'enabled': True,
        'materialized': 'snapshot',
        'persist_docs': {},
        'post-hook': [{'sql': 'insert into blah(a, b) select "1", 1', 'transaction': True}],
        'pre-hook': [],
        'quoting': {},
        'tags': [],
        'vars': {},
        'target_database': 'some_snapshot_db',
        'target_schema': 'some_snapshot_schema',
        'unique_key': 'id',
        'extra': 'even more',
        'strategy': 'timestamp',
        'updated_at': 'last_update',
    }


@pytest.fixture
def complex_timestamp_snapshot_config_object():
    cfg = SnapshotConfig(
        column_types={'a': 'text'},
        materialized='snapshot',
        post_hook=[Hook(sql='insert into blah(a, b) select "1", 1')],
        strategy='timestamp',
        target_database='some_snapshot_db',
        target_schema='some_snapshot_schema',
        updated_at='last_update',
        unique_key='id',
    )
    cfg._extra['extra'] = 'even more'
    return cfg


def test_basic_timestamp_snapshot_config(basic_timestamp_snapshot_config_dict, basic_timestamp_snapshot_config_object):
    cfg = basic_timestamp_snapshot_config_object
    cfg_dict = basic_timestamp_snapshot_config_dict
    assert_symmetric(cfg, cfg_dict)
    pickle.loads(pickle.dumps(cfg))


def test_complex_timestamp_snapshot_config(complex_timestamp_snapshot_config_dict, complex_timestamp_snapshot_config_object):
    cfg = complex_timestamp_snapshot_config_object
    cfg_dict = complex_timestamp_snapshot_config_dict
    assert_symmetric(cfg, cfg_dict, SnapshotConfig)


def test_invalid_missing_updated_at(basic_timestamp_snapshot_config_dict):
    bad_fields = basic_timestamp_snapshot_config_dict
    del bad_fields['updated_at']
    bad_fields['check_cols'] = 'all'
    assert_fails_validation(bad_fields, SnapshotConfig)


@pytest.fixture
def basic_check_snapshot_config_dict():
    return {
        'column_types': {},
        'enabled': True,
        'materialized': 'snapshot',
        'persist_docs': {},
        'post-hook': [],
        'pre-hook': [],
        'quoting': {},
        'tags': [],
        'vars': {},
        'target_database': 'some_snapshot_db',
        'target_schema': 'some_snapshot_schema',
        'unique_key': 'id',
        'strategy': 'check',
        'check_cols': 'all',
    }


@pytest.fixture
def basic_check_snapshot_config_object():
    return SnapshotConfig(
        strategy='check',
        check_cols='all',
        unique_key='id',
        target_database='some_snapshot_db',
        target_schema='some_snapshot_schema',
    )


@pytest.fixture
def complex_set_snapshot_config_dict():
    return {
        'column_types': {'a': 'text'},
        'enabled': True,
        'materialized': 'snapshot',
        'persist_docs': {},
        'post-hook': [{'sql': 'insert into blah(a, b) select "1", 1', 'transaction': True}],
        'pre-hook': [],
        'quoting': {},
        'tags': [],
        'vars': {},
        'target_database': 'some_snapshot_db',
        'target_schema': 'some_snapshot_schema',
        'unique_key': 'id',
        'extra': 'even more',
        'strategy': 'check',
        'check_cols': ['a', 'b'],
    }


@pytest.fixture
def complex_set_snapshot_config_object():
    cfg = SnapshotConfig(
        column_types={'a': 'text'},
        materialized='snapshot',
        post_hook=[Hook(sql='insert into blah(a, b) select "1", 1')],
        strategy='check',
        check_cols=['a', 'b'],
        target_database='some_snapshot_db',
        target_schema='some_snapshot_schema',
        unique_key='id',
    )
    cfg._extra['extra'] = 'even more'
    return cfg


def test_basic_snapshot_config(basic_check_snapshot_config_dict, basic_check_snapshot_config_object):
    cfg_dict = basic_check_snapshot_config_dict
    cfg = basic_check_snapshot_config_object
    assert_symmetric(cfg, cfg_dict, SnapshotConfig)
    pickle.loads(pickle.dumps(cfg))


def test_complex_snapshot_config(complex_set_snapshot_config_dict, complex_set_snapshot_config_object):
    cfg_dict = complex_set_snapshot_config_dict
    cfg = complex_set_snapshot_config_object
    assert_symmetric(cfg, cfg_dict)
    pickle.loads(pickle.dumps(cfg))


def test_invalid_check_wrong_strategy(basic_check_snapshot_config_dict):
    wrong_strategy = basic_check_snapshot_config_dict
    wrong_strategy['strategy'] = 'timestamp'
    assert_fails_validation(wrong_strategy, SnapshotConfig)


def test_invalid_missing_check_cols(basic_check_snapshot_config_dict):
    wrong_fields = basic_check_snapshot_config_dict
    del wrong_fields['check_cols']
    with pytest.raises(ValidationError, match=r"A 'check' snapshot must have 'check_cols'"):
        SnapshotConfig.validate(wrong_fields)


def test_invalid_check_value(basic_check_snapshot_config_dict):
    invalid_check_type = basic_check_snapshot_config_dict
    invalid_check_type['check_cols'] = 'some'
    assert_fails_validation(invalid_check_type, SnapshotConfig)


@pytest.fixture
def basic_timestamp_snapshot_dict():
    return {
        'name': 'foo',
        'root_path': '/root/',
        'resource_type': str(NodeType.Snapshot),
        'path': '/root/x/path.sql',
        'original_file_path': '/root/path.sql',
        'package_name': 'test',
        'raw_sql': 'select * from wherever',
        'unique_id': 'model.test.foo',
        'fqn': ['test', 'models', 'foo'],
        'refs': [],
        'sources': [],
        'depends_on': {'macros': [], 'nodes': []},
        'deferred': False,
        'database': 'test_db',
        'description': '',
        'schema': 'test_schema',
        'alias': 'bar',
        'tags': [],
        'config': {
            'column_types': {},
            'enabled': True,
            'materialized': 'snapshot',
            'persist_docs': {},
            'post-hook': [],
            'pre-hook': [],
            'quoting': {},
            'tags': [],
            'vars': {},
            'target_database': 'some_snapshot_db',
            'target_schema': 'some_snapshot_schema',
            'unique_key': 'id',
            'strategy': 'timestamp',
            'updated_at': 'last_update',
        },
        'docs': {'show': True},
        'columns': {},
        'meta': {},
        'checksum': {'name': 'sha256', 'checksum': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'},
        'unrendered_config': {
            'strategy': 'timestamp',
            'unique_key': 'id',
            'updated_at': 'last_update',
            'target_database': 'some_snapshot_db',
            'target_schema': 'some_snapshot_schema',
        },
    }


@pytest.fixture
def basic_timestamp_snapshot_object():
    return ParsedSnapshotNode(
        package_name='test',
        root_path='/root/',
        path='/root/x/path.sql',
        original_file_path='/root/path.sql',
        raw_sql='select * from wherever',
        name='foo',
        resource_type=NodeType.Snapshot,
        unique_id='model.test.foo',
        fqn=['test', 'models', 'foo'],
        refs=[],
        sources=[],
        depends_on=DependsOn(),
        description='',
        database='test_db',
        schema='test_schema',
        alias='bar',
        tags=[],
        config=SnapshotConfig(
            strategy='timestamp',
            unique_key='id',
            updated_at='last_update',
            target_database='some_snapshot_db',
            target_schema='some_snapshot_schema',
        ),
        checksum=FileHash.from_contents(''),
        unrendered_config={
            'strategy': 'timestamp',
            'unique_key': 'id',
            'updated_at': 'last_update',
            'target_database': 'some_snapshot_db',
            'target_schema': 'some_snapshot_schema',
        },
    )


@pytest.fixture
def basic_intermediate_timestamp_snapshot_object():
    cfg = EmptySnapshotConfig()
    cfg._extra.update({
        'strategy': 'timestamp',
        'unique_key': 'id',
        'updated_at': 'last_update',
        'target_database': 'some_snapshot_db',
        'target_schema': 'some_snapshot_schema',
    })

    return IntermediateSnapshotNode(
        package_name='test',
        root_path='/root/',
        path='/root/x/path.sql',
        original_file_path='/root/path.sql',
        raw_sql='select * from wherever',
        name='foo',
        resource_type=NodeType.Snapshot,
        unique_id='model.test.foo',
        fqn=['test', 'models', 'foo'],
        refs=[],
        sources=[],
        depends_on=DependsOn(),
        description='',
        database='test_db',
        schema='test_schema',
        alias='bar',
        tags=[],
        config=cfg,
        checksum=FileHash.from_contents(''),
        unrendered_config={
            'strategy': 'timestamp',
            'unique_key': 'id',
            'updated_at': 'last_update',
            'target_database': 'some_snapshot_db',
            'target_schema': 'some_snapshot_schema',
        },
    )


@pytest.fixture
def basic_check_snapshot_dict():
    return {
        'name': 'foo',
        'root_path': '/root/',
        'resource_type': str(NodeType.Snapshot),
        'path': '/root/x/path.sql',
        'original_file_path': '/root/path.sql',
        'package_name': 'test',
        'raw_sql': 'select * from wherever',
        'unique_id': 'model.test.foo',
        'fqn': ['test', 'models', 'foo'],
        'refs': [],
        'sources': [],
        'depends_on': {'macros': [], 'nodes': []},
        'database': 'test_db',
        'deferred': False,
        'description': '',
        'schema': 'test_schema',
        'alias': 'bar',
        'tags': [],
        'config': {
            'column_types': {},
            'enabled': True,
            'materialized': 'snapshot',
            'persist_docs': {},
            'post-hook': [],
            'pre-hook': [],
            'quoting': {},
            'tags': [],
            'vars': {},
            'target_database': 'some_snapshot_db',
            'target_schema': 'some_snapshot_schema',
            'unique_key': 'id',
            'strategy': 'check',
            'check_cols': 'all',
        },
        'docs': {'show': True},
        'columns': {},
        'meta': {},
        'checksum': {'name': 'sha256', 'checksum': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'},
        'unrendered_config': {
            'target_database': 'some_snapshot_db',
            'target_schema': 'some_snapshot_schema',
            'unique_key': 'id',
            'strategy': 'check',
            'check_cols': 'all',
        },
    }


@pytest.fixture
def basic_check_snapshot_object():
    return ParsedSnapshotNode(
        package_name='test',
        root_path='/root/',
        path='/root/x/path.sql',
        original_file_path='/root/path.sql',
        raw_sql='select * from wherever',
        name='foo',
        resource_type=NodeType.Snapshot,
        unique_id='model.test.foo',
        fqn=['test', 'models', 'foo'],
        refs=[],
        sources=[],
        depends_on=DependsOn(),
        description='',
        database='test_db',
        schema='test_schema',
        alias='bar',
        tags=[],
        config=SnapshotConfig(
            strategy='check',
            unique_key='id',
            check_cols='all',
            target_database='some_snapshot_db',
            target_schema='some_snapshot_schema',
        ),
        checksum=FileHash.from_contents(''),
        unrendered_config={
            'target_database': 'some_snapshot_db',
            'target_schema': 'some_snapshot_schema',
            'unique_key': 'id',
            'strategy': 'check',
            'check_cols': 'all',
        },
    )


@pytest.fixture
def basic_intermedaite_check_snapshot_object():
    cfg = EmptySnapshotConfig()
    cfg._extra.update({
        'unique_key': 'id',
        'strategy': 'check',
        'check_cols': 'all',
        'target_database': 'some_snapshot_db',
        'target_schema': 'some_snapshot_schema',
    })

    return IntermediateSnapshotNode(
        package_name='test',
        root_path='/root/',
        path='/root/x/path.sql',
        original_file_path='/root/path.sql',
        raw_sql='select * from wherever',
        name='foo',
        resource_type=NodeType.Snapshot,
        unique_id='model.test.foo',
        fqn=['test', 'models', 'foo'],
        refs=[],
        sources=[],
        depends_on=DependsOn(),
        description='',
        database='test_db',
        schema='test_schema',
        alias='bar',
        tags=[],
        config=cfg,
        checksum=FileHash.from_contents(''),
        unrendered_config={
            'target_database': 'some_snapshot_db',
            'target_schema': 'some_snapshot_schema',
            'unique_key': 'id',
            'strategy': 'check',
            'check_cols': 'all',
        },
    )


def test_timestamp_snapshot_ok(basic_timestamp_snapshot_dict, basic_timestamp_snapshot_object, basic_intermediate_timestamp_snapshot_object):
    node_dict = basic_timestamp_snapshot_dict
    node = basic_timestamp_snapshot_object
    inter = basic_intermediate_timestamp_snapshot_object

    assert_symmetric(node, node_dict, ParsedSnapshotNode)
    assert_symmetric(inter, node_dict, IntermediateSnapshotNode)
    assert ParsedSnapshotNode.from_dict(inter.to_dict()) == node
    assert node.is_refable is True
    assert node.is_ephemeral is False
    pickle.loads(pickle.dumps(node))


def test_check_snapshot_ok(basic_check_snapshot_dict, basic_check_snapshot_object, basic_intermedaite_check_snapshot_object):
    node_dict = basic_check_snapshot_dict
    node = basic_check_snapshot_object
    inter = basic_intermedaite_check_snapshot_object

    assert_symmetric(node, node_dict, ParsedSnapshotNode)
    assert_symmetric(inter, node_dict, IntermediateSnapshotNode)
    assert ParsedSnapshotNode.from_dict(inter.to_dict()) == node
    assert node.is_refable is True
    assert node.is_ephemeral is False
    pickle.loads(pickle.dumps(node))


def test_invalid_snapshot_bad_resource_type(basic_timestamp_snapshot_dict):
    bad_resource_type = basic_timestamp_snapshot_dict
    bad_resource_type['resource_type'] = str(NodeType.Model)
    assert_fails_validation(bad_resource_type, ParsedSnapshotNode)


def test_basic_parsed_node_patch(basic_parsed_model_patch_object, basic_parsed_model_patch_dict):
    assert_symmetric(basic_parsed_model_patch_object, basic_parsed_model_patch_dict)


@pytest.fixture
def populated_parsed_node_patch_dict():
    return {
        'name': 'foo',
        'description': 'The foo model',
        'original_file_path': '/path/to/schema.yml',
        'columns': {
            'a': {
                'name': 'a',
                'description': 'a text field',
                'meta': {},
                'tags': [],
            },
        },
        'docs': {'show': False},
        'meta': {'key': ['value']},
        'yaml_key': 'models',
        'package_name': 'test',
    }


@pytest.fixture
def populated_parsed_node_patch_object():
    return ParsedNodePatch(
        name='foo',
        description='The foo model',
        original_file_path='/path/to/schema.yml',
        columns={'a': ColumnInfo(name='a', description='a text field', meta={})},
        meta={'key': ['value']},
        yaml_key='models',
        package_name='test',
        docs=Docs(show=False),
    )


def test_populated_parsed_node_patch(populated_parsed_node_patch_dict, populated_parsed_node_patch_object):
    assert_symmetric(populated_parsed_node_patch_object, populated_parsed_node_patch_dict)


class TestParsedMacro(ContractTestCase):
    ContractType = ParsedMacro

    def _ok_dict(self):
        return {
            'name': 'foo',
            'path': '/root/path.sql',
            'original_file_path': '/root/path.sql',
            'package_name': 'test',
            'macro_sql': '{% macro foo() %}select 1 as id{% endmacro %}',
            'root_path': '/root/',
            'resource_type': 'macro',
            'unique_id': 'macro.test.foo',
            'tags': [],
            'depends_on': {'macros': []},
            'meta': {},
            'description': 'my macro description',
            'docs': {'show': True},
            'arguments': [],
        }

    def test_ok(self):
        macro_dict = self._ok_dict()
        macro = self.ContractType(
            name='foo',
            path='/root/path.sql',
            original_file_path='/root/path.sql',
            package_name='test',
            macro_sql='{% macro foo() %}select 1 as id{% endmacro %}',
            root_path='/root/',
            resource_type=NodeType.Macro,
            unique_id='macro.test.foo',
            tags=[],
            depends_on=MacroDependsOn(),
            meta={},
            description='my macro description',
            arguments=[],
        )
        self.assert_symmetric(macro, macro_dict)
        self.assertEqual(macro.local_vars(), {})
        pickle.loads(pickle.dumps(macro))

    def test_invalid_missing_unique_id(self):
        bad_missing_uid = self._ok_dict()
        del bad_missing_uid['unique_id']
        self.assert_fails_validation(bad_missing_uid)

    def test_invalid_extra_field(self):
        bad_extra_field = self._ok_dict()
        bad_extra_field['extra'] = 'too many fields'
        self.assert_fails_validation(bad_extra_field)


class TestParsedDocumentation(ContractTestCase):
    ContractType = ParsedDocumentation

    def _ok_dict(self):
        return {
            'block_contents': 'some doc contents',
            'name': 'foo',
            'original_file_path': '/root/docs/doc.md',
            'package_name': 'test',
            'path': '/root/docs',
            'root_path': '/root',
            'unique_id': 'test.foo',
        }

    def test_ok(self):
        doc_dict = self._ok_dict()
        doc = self.ContractType(
            package_name='test',
            root_path='/root',
            path='/root/docs',
            original_file_path='/root/docs/doc.md',
            name='foo',
            unique_id='test.foo',
            block_contents='some doc contents'
        )
        self.assert_symmetric(doc, doc_dict)
        pickle.loads(pickle.dumps(doc))

    def test_invalid_missing(self):
        bad_missing_contents = self._ok_dict()
        del bad_missing_contents['block_contents']
        self.assert_fails_validation(bad_missing_contents)

    def test_invalid_extra(self):
        bad_extra_field = self._ok_dict()
        bad_extra_field['extra'] = 'more'
        self.assert_fails_validation(bad_extra_field)


@pytest.fixture
def minimum_parsed_source_definition_dict():
    return {
        'package_name': 'test',
        'root_path': '/root',
        'path': '/root/models/sources.yml',
        'original_file_path': '/root/models/sources.yml',
        'database': 'some_db',
        'schema': 'some_schema',
        'fqn': ['test', 'source', 'my_source', 'my_source_table'],
        'source_name': 'my_source',
        'name': 'my_source_table',
        'source_description': 'my source description',
        'loader': 'stitch',
        'identifier': 'my_source_table',
        'resource_type': str(NodeType.Source),
        'unique_id': 'test.source.my_source.my_source_table',
    }


@pytest.fixture
def basic_parsed_source_definition_dict():
    return {
        'package_name': 'test',
        'root_path': '/root',
        'path': '/root/models/sources.yml',
        'original_file_path': '/root/models/sources.yml',
        'database': 'some_db',
        'schema': 'some_schema',
        'fqn': ['test', 'source', 'my_source', 'my_source_table'],
        'source_name': 'my_source',
        'name': 'my_source_table',
        'source_description': 'my source description',
        'loader': 'stitch',
        'identifier': 'my_source_table',
        'resource_type': str(NodeType.Source),
        'description': '',
        'columns': {},
        'quoting': {},
        'unique_id': 'test.source.my_source.my_source_table',
        'meta': {},
        'source_meta': {},
        'tags': [],
        'config': {
            'enabled': True,
        },
        'unrendered_config': {},
    }


@pytest.fixture
def basic_parsed_source_definition_object():
    return ParsedSourceDefinition(
        columns={},
        database='some_db',
        description='',
        fqn=['test', 'source', 'my_source', 'my_source_table'],
        identifier='my_source_table',
        loader='stitch',
        name='my_source_table',
        original_file_path='/root/models/sources.yml',
        package_name='test',
        path='/root/models/sources.yml',
        quoting=Quoting(),
        resource_type=NodeType.Source,
        root_path='/root',
        schema='some_schema',
        source_description='my source description',
        source_name='my_source',
        unique_id='test.source.my_source.my_source_table',
        tags=[],
        config=SourceConfig(),
    )


@pytest.fixture
def complex_parsed_source_definition_dict():
    return {
        'package_name': 'test',
        'root_path': '/root',
        'path': '/root/models/sources.yml',
        'original_file_path': '/root/models/sources.yml',
        'database': 'some_db',
        'schema': 'some_schema',
        'fqn': ['test', 'source', 'my_source', 'my_source_table'],
        'source_name': 'my_source',
        'name': 'my_source_table',
        'source_description': 'my source description',
        'loader': 'stitch',
        'identifier': 'my_source_table',
        'resource_type': str(NodeType.Source),
        'description': '',
        'columns': {},
        'quoting': {},
        'unique_id': 'test.source.my_source.my_source_table',
        'meta': {},
        'source_meta': {},
        'tags': ['my_tag'],
        'config': {
            'enabled': True,
        },
        'freshness': {
            'warn_after': {'period': 'hour', 'count': 1},
        },
        'loaded_at_field': 'loaded_at',
        'unrendered_config': {},
    }


@pytest.fixture
def complex_parsed_source_definition_object():
    return ParsedSourceDefinition(
        columns={},
        database='some_db',
        description='',
        fqn=['test', 'source', 'my_source', 'my_source_table'],
        identifier='my_source_table',
        loader='stitch',
        name='my_source_table',
        original_file_path='/root/models/sources.yml',
        package_name='test',
        path='/root/models/sources.yml',
        quoting=Quoting(),
        resource_type=NodeType.Source,
        root_path='/root',
        schema='some_schema',
        source_description='my source description',
        source_name='my_source',
        unique_id='test.source.my_source.my_source_table',
        tags=['my_tag'],
        config=SourceConfig(),
        freshness=FreshnessThreshold(warn_after=Time(period=TimePeriod.hour, count=1)),
        loaded_at_field='loaded_at',
    )


def test_basic_source_definition(minimum_parsed_source_definition_dict, basic_parsed_source_definition_dict, basic_parsed_source_definition_object):
    node = basic_parsed_source_definition_object
    node_dict = basic_parsed_source_definition_dict
    minimum = minimum_parsed_source_definition_dict

    assert_symmetric(node, node_dict, ParsedSourceDefinition)

    assert node.is_ephemeral is False
    assert node.is_refable is False
    assert node.has_freshness is False

    assert_from_dict(node, minimum, ParsedSourceDefinition)
    pickle.loads(pickle.dumps(node))


def test_invalid_missing(minimum_parsed_source_definition_dict):
    bad_missing_name = minimum_parsed_source_definition_dict
    del bad_missing_name['name']
    assert_fails_validation(bad_missing_name, ParsedSourceDefinition)


def test_invalid_bad_resource_type(minimum_parsed_source_definition_dict):
    bad_resource_type = minimum_parsed_source_definition_dict
    bad_resource_type['resource_type'] = str(NodeType.Model)
    assert_fails_validation(bad_resource_type, ParsedSourceDefinition)


def test_complex_source_definition(complex_parsed_source_definition_dict, complex_parsed_source_definition_object):
    node = complex_parsed_source_definition_object
    node_dict = complex_parsed_source_definition_dict
    assert_symmetric(node, node_dict, ParsedSourceDefinition)

    assert node.is_ephemeral is False
    assert node.is_refable is False
    assert node.has_freshness is True

    pickle.loads(pickle.dumps(node))


def test_source_no_loaded_at(complex_parsed_source_definition_object):
    node = complex_parsed_source_definition_object
    assert node.has_freshness is True
    # no loaded_at_field -> does not have freshness
    node.loaded_at_field = None
    assert node.has_freshness is False


def test_source_no_freshness(complex_parsed_source_definition_object):
    node = complex_parsed_source_definition_object
    assert node.has_freshness is True
    node.freshness = None
    assert node.has_freshness is False


unchanged_source_definitions = [
    lambda u: (u, u.replace(tags=['mytag'])),
    lambda u: (u, u.replace(meta={'a': 1000})),
]

changed_source_definitions = [
    lambda u: (u, u.replace(freshness=FreshnessThreshold(warn_after=Time(period=TimePeriod.hour, count=1)), loaded_at_field='loaded_at')),
    lambda u: (u, u.replace(loaded_at_field='loaded_at')),
    lambda u: (u, u.replace(freshness=FreshnessThreshold(error_after=Time(period=TimePeriod.hour, count=1)))),
    lambda u: (u, u.replace(quoting=Quoting(identifier=True))),
    lambda u: (u, u.replace(database='other_database')),
    lambda u: (u, u.replace(schema='other_schema')),
    lambda u: (u, u.replace(identifier='identifier')),
]


@pytest.mark.parametrize('func', unchanged_source_definitions)
def test_compare_unchanged_parsed_source_definition(func, basic_parsed_source_definition_object):
    node, compare = func(basic_parsed_source_definition_object)
    assert node.same_contents(compare)


@pytest.mark.parametrize('func', changed_source_definitions)
def test_compare_changed_source_definition(func, basic_parsed_source_definition_object):
    node, compare = func(basic_parsed_source_definition_object)
    assert not node.same_contents(compare)


@pytest.fixture
def minimal_parsed_exposure_dict():
    return {
        'name': 'my_exposure',
        'type': 'notebook',
        'owner': {
            'email': 'test@example.com',
        },
        'fqn': ['test', 'exposures', 'my_exposure'],
        'unique_id': 'exposure.test.my_exposure',
        'package_name': 'test',
        'path': 'models/something.yml',
        'root_path': '/usr/src/app',
        'original_file_path': 'models/something.yml',
        'description': ''
    }


@pytest.fixture
def basic_parsed_exposure_dict():
    return {
        'name': 'my_exposure',
        'type': 'notebook',
        'owner': {
            'email': 'test@example.com',
        },
        'resource_type': 'exposure',
        'depends_on': {
            'nodes': [],
            'macros': [],
        },
        'refs': [],
        'sources': [],
        'fqn': ['test', 'exposures', 'my_exposure'],
        'unique_id': 'exposure.test.my_exposure',
        'package_name': 'test',
        'path': 'models/something.yml',
        'root_path': '/usr/src/app',
        'original_file_path': 'models/something.yml',
        'description': ''
    }


@pytest.fixture
def basic_parsed_exposure_object():
    return ParsedExposure(
        name='my_exposure',
        type=ExposureType.Notebook,
        fqn=['test', 'exposures', 'my_exposure'],
        unique_id='exposure.test.my_exposure',
        package_name='test',
        path='models/something.yml',
        root_path='/usr/src/app',
        original_file_path='models/something.yml',
        owner=ExposureOwner(email='test@example.com'),
        description=''
    )


@pytest.fixture
def complex_parsed_exposure_dict():
    return {
        'name': 'my_exposure',
        'type': 'analysis',
        'owner': {
            'email': 'test@example.com',
            'name': 'A Name',
        },
        'resource_type': 'exposure',
        'maturity': 'low',
        'url': 'https://example.com/analyses/1',
        'description': 'my description',
        'depends_on': {
            'nodes': ['models.test.my_model'],
            'macros': [],
        },
        'refs': [],
        'sources': [],
        'fqn': ['test', 'exposures', 'my_exposure'],
        'unique_id': 'exposure.test.my_exposure',
        'package_name': 'test',
        'path': 'models/something.yml',
        'root_path': '/usr/src/app',
        'original_file_path': 'models/something.yml',
    }


@pytest.fixture
def complex_parsed_exposure_object():
    return ParsedExposure(
        name='my_exposure',
        type=ExposureType.Analysis,
        owner=ExposureOwner(email='test@example.com', name='A Name'),
        maturity=MaturityType.Low,
        url='https://example.com/analyses/1',
        description='my description',
        depends_on=DependsOn(nodes=['models.test.my_model']),
        fqn=['test', 'exposures', 'my_exposure'],
        unique_id='exposure.test.my_exposure',
        package_name='test',
        path='models/something.yml',
        root_path='/usr/src/app',
        original_file_path='models/something.yml',
    )


def test_basic_parsed_exposure(minimal_parsed_exposure_dict, basic_parsed_exposure_dict, basic_parsed_exposure_object):
    assert_symmetric(basic_parsed_exposure_object, basic_parsed_exposure_dict, ParsedExposure)
    assert_from_dict(basic_parsed_exposure_object, minimal_parsed_exposure_dict, ParsedExposure)
    pickle.loads(pickle.dumps(basic_parsed_exposure_object))


def test_complex_parsed_exposure(complex_parsed_exposure_dict, complex_parsed_exposure_object):
    assert_symmetric(complex_parsed_exposure_object, complex_parsed_exposure_dict, ParsedExposure)


unchanged_parsed_exposures = [
    lambda u: (u, u),
]


changed_parsed_exposures = [
    lambda u: (u, u.replace(fqn=u.fqn[:-1]+['something', u.fqn[-1]])),
    lambda u: (u, u.replace(type=ExposureType.ML)),
    lambda u: (u, u.replace(owner=u.owner.replace(name='My Name'))),
    lambda u: (u, u.replace(maturity=MaturityType.Medium)),
    lambda u: (u, u.replace(url='https://example.com/dashboard/1')),
    lambda u: (u, u.replace(description='My description')),
    lambda u: (u, u.replace(depends_on=DependsOn(nodes=['model.test.blah']))),
]


@pytest.mark.parametrize('func', unchanged_parsed_exposures)
def test_compare_unchanged_parsed_exposure(func, basic_parsed_exposure_object):
    node, compare = func(basic_parsed_exposure_object)
    assert node.same_contents(compare)


@pytest.mark.parametrize('func', changed_parsed_exposures)
def test_compare_changed_exposure(func, basic_parsed_exposure_object):
    node, compare = func(basic_parsed_exposure_object)
    assert not node.same_contents(compare)
