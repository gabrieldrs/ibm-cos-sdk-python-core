# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
from tests import unittest
import mock
from nose.tools import assert_equal

import ibm_botocore
import ibm_botocore.session as session
from ibm_botocore.configprovider import ConfigValueStore
from ibm_botocore.configprovider import BaseProvider
from ibm_botocore.configprovider import InstanceVarProvider
from ibm_botocore.configprovider import EnvironmentProvider
from ibm_botocore.configprovider import ScopedConfigProvider
from ibm_botocore.configprovider import ConstantProvider
from ibm_botocore.configprovider import ChainProvider
from ibm_botocore.configprovider import ConfigChainFactory


class TestConfigChainFactory(unittest.TestCase):
    def assert_chain_does_provide(self, instance_map, environ_map,
                                  scoped_config_map, create_config_chain_args,
                                  expected_value):
        fake_session = mock.Mock(spec=session.Session)
        fake_session.get_scoped_config.return_value = scoped_config_map
        fake_session.instance_variables.return_value = instance_map
        builder = ConfigChainFactory(fake_session, environ=environ_map)
        chain = builder.create_config_chain(
            **create_config_chain_args
        )
        value = chain.provide()
        self.assertEqual(value, expected_value)

    def test_chain_builder_can_provide_instance(self):
        self.assert_chain_does_provide(
            instance_map={'instance_var': 'from-instance'},
            environ_map={},
            scoped_config_map={},
            create_config_chain_args={
                'instance_name': 'instance_var',
            },
            expected_value='from-instance',
        )

    def test_chain_builder_can_skip_instance(self):
        self.assert_chain_does_provide(
            instance_map={'wrong_instance_var': 'instance'},
            environ_map={'ENV_VAR': 'env'},
            scoped_config_map={},
            create_config_chain_args={
                'instance_name': 'instance_var',
                'env_var_names': 'ENV_VAR',
            },
            expected_value='env',
        )

    def test_chain_builder_can_provide_env_var(self):
        self.assert_chain_does_provide(
            instance_map={},
            environ_map={'ENV_VAR': 'from-env'},
            scoped_config_map={},
            create_config_chain_args={
                'env_var_names': 'ENV_VAR',
            },
            expected_value='from-env',
        )

    def test_chain_builder_can_provide_config_var(self):
        self.assert_chain_does_provide(
            instance_map={},
            environ_map={},
            scoped_config_map={'config_var': 'from-config'},
            create_config_chain_args={
                'config_property_name': 'config_var',
            },
            expected_value='from-config',
        )

    def test_chain_builder_can_provide_default(self):
        self.assert_chain_does_provide(
            instance_map={},
            environ_map={},
            scoped_config_map={},
            create_config_chain_args={
                'default': 'from-default'
            },
            expected_value='from-default',
        )

    def test_chain_provider_does_follow_priority_instance_var(self):
        self.assert_chain_does_provide(
            instance_map={'instance_var': 'from-instance'},
            environ_map={'ENV_VAR': 'from-env'},
            scoped_config_map={'config_var': 'from-config'},
            create_config_chain_args={
                'instance_name': 'instance_var',
                'env_var_names': 'ENV_VAR',
                'config_property_name': 'config_var',
                'default': 'from-default',
            },
            expected_value='from-instance',
        )

    def test_chain_provider_does_follow_priority_env_var(self):
        self.assert_chain_does_provide(
            instance_map={'wrong_instance_var': 'from-instance'},
            environ_map={'ENV_VAR': 'from-env'},
            scoped_config_map={'config_var': 'from-confi'},
            create_config_chain_args={
                'instance_name': 'instance_var',
                'env_var_names': 'ENV_VAR',
                'config_property_name': 'config_var',
                'default': 'from-default',
            },
            expected_value='from-env',
        )

    def test_chain_provider_does_follow_priority_config(self):
        self.assert_chain_does_provide(
            instance_map={'wrong_instance_var': 'from-instance'},
            environ_map={'WRONG_ENV_VAR': 'from-env'},
            scoped_config_map={'config_var': 'from-config'},
            create_config_chain_args={
                'instance_name': 'instance_var',
                'env_var_names': 'ENV_VAR',
                'config_property_name': 'config_var',
                'default': 'from-default',
            },
            expected_value='from-config',
        )

    def test_chain_provider_does_follow_priority_default(self):
        self.assert_chain_does_provide(
            instance_map={'wrong_instance_var': 'from-instance'},
            environ_map={'WRONG_ENV_VAR': 'from-env'},
            scoped_config_map={'wrong_config_var': 'from-config'},
            create_config_chain_args={
                'instance_name': 'instance_var',
                'env_var_names': 'ENV_VAR',
                'config_property_name': 'config_var',
                'default': 'from-default',
            },
            expected_value='from-default',
        )


class TestConfigValueStore(unittest.TestCase):
    def test_does_provide_none_if_no_variable_exists(self):
        provider = ConfigValueStore()
        value = provider.get_config_variable('fake_variable')
        self.assertIsNone(value)

    def test_does_provide_value_if_variable_exists(self):
        mock_value_provider = mock.Mock(spec=BaseProvider)
        mock_value_provider.provide.return_value = 'foo'
        provider = ConfigValueStore(mapping={
            'fake_variable': mock_value_provider,
        })
        value = provider.get_config_variable('fake_variable')
        self.assertEqual(value, 'foo')

    def test_can_set_variable(self):
        provider = ConfigValueStore()
        provider.set_config_variable('fake_variable', 'foo')
        value = provider.get_config_variable('fake_variable')
        self.assertEquals(value, 'foo')

    def test_can_set_config_provider(self):
        foo_value_provider = mock.Mock(spec=BaseProvider)
        foo_value_provider.provide.return_value = 'foo'
        provider = ConfigValueStore(mapping={
            'fake_variable': foo_value_provider,
        })

        value = provider.get_config_variable('fake_variable')
        self.assertEqual(value, 'foo')

        bar_value_provider = mock.Mock(spec=BaseProvider)
        bar_value_provider.provide.return_value = 'bar'
        provider.set_config_provider('fake_variable', bar_value_provider)

        value = provider.get_config_variable('fake_variable')
        self.assertEqual(value, 'bar')


class TestInstanceVarProvider(unittest.TestCase):
    def assert_provides_value(self, name, instance_map, expected_value):
        fake_session = mock.Mock(spec=session.Session)
        fake_session.instance_variables.return_value = instance_map

        provider = InstanceVarProvider(
            instance_var=name,
            session=fake_session,
        )
        value = provider.provide()
        self.assertEqual(value, expected_value)

    def test_can_provide_value(self):
        self.assert_provides_value(
            name='foo',
            instance_map={'foo': 'bar'},
            expected_value='bar',
        )

    def test_does_provide_none_if_value_not_in_dict(self):
        self.assert_provides_value(
            name='foo',
            instance_map={},
            expected_value=None,
        )


class TestEnvironmentProvider(unittest.TestCase):
    def assert_does_provide(self, env, names, expected_value):
        provider = EnvironmentProvider(names=names, env=env)
        value = provider.provide()
        self.assertEqual(value, expected_value)

    def test_does_provide_none_if_no_variable_exists(self):
        self.assert_does_provide(
            names='FOO',
            env={},
            expected_value=None,
        )

    def test_does_provide_value_if_variable_exists(self):
        self.assert_does_provide(
            names='FOO',
            env={
                'FOO': 'bar',
            },
            expected_value='bar',
        )

    def test_does_provide_none_if_no_variable_exists_in_list(self):
        self.assert_does_provide(
            names=['FOO'],
            env={},
            expected_value=None,
        )

    def test_does_provide_value_if_variable_exists_in_list(self):
        self.assert_does_provide(
            names=['FOO'],
            env={
                'FOO': 'bar',
            },
            expected_value='bar',
        )

    def test_does_provide_first_non_none_value_first(self):
        self.assert_does_provide(
            names=['FOO', 'BAR'],
            env={
                'FOO': 'baz',
            },
            expected_value='baz',
        )

    def test_does_provide_first_non_none_value_second(self):
        self.assert_does_provide(
            names=['FOO', 'BAR'],
            env={
                'BAR': 'baz',
            },
            expected_value='baz',
        )

    def test_does_provide_none_if_all_list_variables_are_none(self):
        self.assert_does_provide(
            names=['FOO', 'BAR'],
            env={},
            expected_value=None,
        )

    def test_does_provide_first_value_when_both_exist(self):
        self.assert_does_provide(
            names=['FOO', 'BAR'],
            env={
                'FOO': 'baz',
                'BAR': 'buz',
            },
            expected_value='baz',
        )


class TestScopedConfigProvider(unittest.TestCase):
    def assert_provides_value(self, config_file_values, config_var_name,
                              expected_value):
        fake_session = mock.Mock(spec=session.Session)
        fake_session.get_scoped_config.return_value = config_file_values
        property_provider = ScopedConfigProvider(
            config_var_name=config_var_name,
            session=fake_session,
        )
        value = property_provider.provide()
        self.assertEqual(value, expected_value)

    def test_can_provide_value(self):
        self.assert_provides_value(
            config_file_values={
                'foo': 'bar'
            },
            config_var_name='foo',
            expected_value='bar',
        )

    def test_does_provide_none_if_var_not_in_config(self):
        self.assert_provides_value(
            config_file_values={
                'foo': 'bar'
            },
            config_var_name='no_such_var',
            expected_value=None,
        )


def _make_provider_that_returns(return_value):
    provider = mock.Mock(spec=BaseProvider)
    provider.provide.return_value = return_value
    return provider


def _make_providers_that_return(return_values):
    mocks = []
    for return_value in return_values:
        provider = _make_provider_that_returns(return_value)
        mocks.append(provider)
    return mocks


def assert_chain_does_provide(providers, expected_value):
    provider = ChainProvider(
        providers=providers,
    )
    value = provider.provide()
    assert_equal(value, expected_value)


def test_chain_provider():
    # Each case is a tuple with the first element being the expected return
    # value form the ChainProvider. The second value being a list of return
    # values from the individual providers that are in the chain.
    cases = [
        (None, []),
        (None, [None]),
        ('foo', ['foo']),
        ('foo', ['foo', 'bar']),
        ('bar', [None, 'bar']),
        ('foo', ['foo', None]),
        ('baz', [None, None, 'baz']),
        ('bar', [None, 'bar', None]),
        ('foo', ['foo', 'bar', None]),
        ('foo', ['foo', 'bar', 'baz']),
    ]
    for case in cases:
        yield assert_chain_does_provide, \
            _make_providers_that_return(case[1]), \
            case[0]


class TestChainProvider(unittest.TestCase):
    def test_can_convert_provided_value(self):
        chain_provider = ChainProvider(
            providers=_make_providers_that_return(['1']),
            conversion_func=int,
        )
        value = chain_provider.provide()
        self.assertIsInstance(value, int)
        self.assertEqual(value, 1)


class TestConstantProvider(unittest.TestCase):
    def test_can_provide_value(self):
        provider = ConstantProvider(value='foo')
        value = provider.provide()
        self.assertEqual(value, 'foo')
