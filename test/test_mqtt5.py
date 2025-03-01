# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

from concurrent.futures import Future
from awscrt import mqtt5, io, http, exceptions
from test import NativeResourceTest
import enum
import os
import unittest
import pathlib
import uuid
import time

"""
# Environmental variables used by mqtt5 bindings tests

# AWS_TEST_MQTT5_DIRECT_MQTT_HOST - host to connect to in direct mqtt tests
# AWS_TEST_MQTT5_DIRECT_MQTT_PORT - port to connect to in direct mqtt tests
# AWS_TEST_MQTT5_DIRECT_MQTT_BASIC_AUTH_HOST - host to connect to in direct mqtt basic authentication tests
# AWS_TEST_MQTT5_DIRECT_MQTT_BASIC_AUTH_PORT - port to connect to in direct mqtt basic authentication tests
# AWS_TEST_MQTT5_DIRECT_MQTT_TLS_HOST - host to connect to in direct mqtt tls tests
# AWS_TEST_MQTT5_DIRECT_MQTT_TLS_PORT - port to connect to in direct mqtt tls tests
# AWS_TEST_MQTT5_WS_MQTT_HOST - host to connect to in websocket tests
# AWS_TEST_MQTT5_WS_MQTT_PORT - port to connect to in websocket tests
# AWS_TEST_MQTT5_WS_MQTT_BASIC_AUTH_HOST - host to connect to in websocket basic authentication tests
# AWS_TEST_MQTT5_WS_MQTT_BASIC_AUTH_PORT - port to connect to in websocket basic authentication tests
# AWS_TEST_MQTT5_WS_MQTT_TLS_HOST - host to connect to in websocket tls tests
# AWS_TEST_MQTT5_WS_MQTT_TLS_PORT - port to connect to in websocket tls tests
# AWS_TEST_MQTT5_IOT_CORE_HOST - host to connect to in MTLS tests
# AWS_TEST_MQTT5_BASIC_AUTH_USERNAME - username to use in basic authentication tests
# AWS_TEST_MQTT5_BASIC_AUTH_PASSWORD - password to use in basic authentication tests
# AWS_TEST_MQTT5_PROXY_HOST - name of http proxy host to use in proxy-based tests
# AWS_TEST_MQTT5_PROXY_PORT - port of http proxy host to use in proxy-based tests
# AWS_TEST_MQTT5_CERTIFICATE_FILE - certificate file path
# AWS_TEST_MQTT5_KEY_FILE - private key file path
# AWS_TEST_MQTT5_IOT_KEY_PATH - private key file path for MTLS tests
# AWS_TEST_MQTT5_IOT_CERTIFICATE_PATH - certificate file path for MTLS tests

"""

TIMEOUT = 100.0

AuthType = enum.Enum('AuthType', ['DIRECT',
                                  'DIRECT_BASIC_AUTH',
                                  'DIRECT_TLS',
                                  'DIRECT_MUTUAL_TLS',
                                  'DIRECT_PROXY',
                                  'WS',
                                  'WS_BASIC_AUTH',
                                  'WS_TLS',
                                  'WS_PROXY',
                                  'NO_APPLICATION',
                                  'DIRECT_HOST_ONLY',
                                  'DIRECT_HOST_AND_PORT_ONLY',
                                  'WS_BAD_PORT',
                                  'DIRECT_BASIC_AUTH_BAD',
                                  'DOUBLE_CLIENT_ID_FAILURE'])


class Config:
    def __init__(self, auth_type: AuthType):

        if auth_type == AuthType.DIRECT or auth_type == AuthType.DOUBLE_CLIENT_ID_FAILURE or auth_type == AuthType.DIRECT_HOST_AND_PORT_ONLY:
            self.endpoint = self._get_env("AWS_TEST_MQTT5_DIRECT_MQTT_HOST")
            self.port = self._get_env("AWS_TEST_MQTT5_DIRECT_MQTT_PORT")

        elif auth_type == AuthType.DIRECT_HOST_ONLY:
            self.endpoint = self._get_env("AWS_TEST_MQTT5_DIRECT_MQTT_HOST")

        elif auth_type == AuthType.DIRECT_BASIC_AUTH or auth_type == AuthType.DIRECT_BASIC_AUTH_BAD:
            self.endpoint = self._get_env("AWS_TEST_MQTT5_DIRECT_MQTT_BASIC_AUTH_HOST")
            self.port = self._get_env("AWS_TEST_MQTT5_DIRECT_MQTT_BASIC_AUTH_PORT")
            self.username = self._get_env('AWS_TEST_MQTT5_BASIC_AUTH_USERNAME')
            self.password = self._get_env('AWS_TEST_MQTT5_BASIC_AUTH_PASSWORD')

        elif auth_type == AuthType.DIRECT_TLS:
            self.endpoint = self._get_env("AWS_TEST_MQTT5_DIRECT_MQTT_TLS_HOST")
            self.port = self._get_env("AWS_TEST_MQTT5_DIRECT_MQTT_TLS_PORT")
            self.key_path = self._get_env('AWS_TEST_MQTT5_KEY_FILE')
            self.key = pathlib.Path(self.key_path).read_text().encode('utf-8')
            self.cert_path = self._get_env('AWS_TEST_MQTT5_CERTIFICATE_FILE')
            self.cert = pathlib.Path(self.cert_path).read_text().encode('utf-8')

        elif auth_type == AuthType.DIRECT_MUTUAL_TLS:
            self.endpoint = self._get_env("AWS_TEST_MQTT5_IOT_CORE_HOST")
            self.port = 8883
            self.key_path = self._get_env('AWS_TEST_MQTT5_IOT_KEY_PATH')
            self.key = pathlib.Path(self.key_path).read_text().encode('utf-8')
            self.cert_path = self._get_env('AWS_TEST_MQTT5_IOT_CERTIFICATE_PATH')
            self.cert = pathlib.Path(self.cert_path).read_text().encode('utf-8')

        elif auth_type == AuthType.WS:
            self.endpoint = self._get_env("AWS_TEST_MQTT5_WS_MQTT_HOST")
            self.port = self._get_env("AWS_TEST_MQTT5_WS_MQTT_PORT")

        elif auth_type == AuthType.WS_BAD_PORT:
            self.endpoint = self._get_env("AWS_TEST_MQTT5_WS_MQTT_HOST")
            self.port = 444

        elif auth_type == AuthType.WS_BASIC_AUTH:
            self.endpoint = self._get_env("AWS_TEST_MQTT5_WS_MQTT_BASIC_AUTH_HOST")
            self.port = self._get_env("AWS_TEST_MQTT5_WS_MQTT_BASIC_AUTH_PORT")
            self.username = self._get_env('AWS_TEST_MQTT5_BASIC_AUTH_USERNAME')
            self.password = self._get_env('AWS_TEST_MQTT5_BASIC_AUTH_PASSWORD')

        elif auth_type == AuthType.WS_TLS:
            self.endpoint = self._get_env("AWS_TEST_MQTT5_WS_MQTT_TLS_HOST")
            self.port = self._get_env("AWS_TEST_MQTT5_WS_MQTT_TLS_PORT")
            self.key_path = self._get_env('AWS_TEST_MQTT5_KEY_FILE')
            self.key = pathlib.Path(self.key_path).read_text().encode('utf-8')
            self.cert_path = self._get_env('AWS_TEST_MQTT5_CERTIFICATE_FILE')
            self.cert = pathlib.Path(self.cert_path).read_text().encode('utf-8')

        elif auth_type == AuthType.DIRECT_PROXY:
            self.endpoint = self._get_env("AWS_TEST_MQTT5_DIRECT_MQTT_TLS_HOST")
            self.port = self._get_env("AWS_TEST_MQTT5_DIRECT_MQTT_TLS_PORT")
            self.proxy_endpoint = self._get_env("AWS_TEST_MQTT5_PROXY_HOST")
            self.proxy_port = self._get_env("AWS_TEST_MQTT5_PROXY_PORT")
            self.key_path = self._get_env('AWS_TEST_MQTT5_KEY_FILE')
            self.key = pathlib.Path(self.key_path).read_text().encode('utf-8')
            self.cert_path = self._get_env('AWS_TEST_MQTT5_CERTIFICATE_FILE')
            self.cert = pathlib.Path(self.cert_path).read_text().encode('utf-8')

        elif auth_type == AuthType.WS_PROXY:
            self.endpoint = self._get_env("AWS_TEST_MQTT5_WS_MQTT_HOST")
            self.port = self._get_env("AWS_TEST_MQTT5_WS_MQTT_PORT")
            self.proxy_endpoint = self._get_env("AWS_TEST_MQTT5_PROXY_HOST")
            self.proxy_port = self._get_env("AWS_TEST_MQTT5_PROXY_PORT")
            self.key_path = self._get_env('AWS_TEST_MQTT5_KEY_FILE')
            self.key = pathlib.Path(self.key_path).read_text().encode('utf-8')
            self.cert_path = self._get_env('AWS_TEST_MQTT5_CERTIFICATE_FILE')
            self.cert = pathlib.Path(self.cert_path).read_text().encode('utf-8')

    def _get_env(self, name):
        val = os.environ.get(name)
        if not val:
            raise unittest.SkipTest(f"test requires env var: {name}")
        return val


def create_client_id():
    return f"aws-crt-python-unit-test-{uuid.uuid4()}"


class Mqtt5TestCallbacks():
    def __init__(self):
        self.on_publish_receive_expected = 0
        self.on_publish_received_counter = 0
        self.last_exception = None

        self.negotiated_settings = None
        self.connack_packet = None
        self.publish_packet = None

        self.future_connection_success = Future()
        self.future_stopped = Future()
        self.future_connection_failure = Future()
        self.future_disconnection = Future()
        self.future_publish_received = Future()
        self.future_expected_publishes_received = Future()

    def ws_handshake_transform(self, transform_args):
        transform_args.set_done()

    def on_publish_received(self, publish_received_data: mqtt5.PublishReceivedData):
        self.on_publish_received_counter += 1
        if self.future_publish_received and not self.future_publish_received.done():
            self.future_publish_received.set_result(publish_received_data.publish_packet)

        if self.on_publish_receive_expected > 0 and self.on_publish_received_counter == self.on_publish_receive_expected and not self.future_expected_publishes_received.done():
            self.future_expected_publishes_received.set_result(True)

    def on_lifecycle_stopped(self, lifecycle_stopped: mqtt5.LifecycleStoppedData):
        if self.future_stopped:
            self.future_stopped.set_result(None)

    def on_lifecycle_attempting_connect(self, lifecycle_attempting_connect: mqtt5.LifecycleAttemptingConnectData):
        pass

    def on_lifecycle_connection_success(self, lifecycle_connection_success: mqtt5.LifecycleConnectSuccessData):
        self.negotiated_settings = lifecycle_connection_success.negotiated_settings
        self.connack_packet = lifecycle_connection_success.connack_packet
        if self.future_connection_success:
            self.future_connection_success.set_result(lifecycle_connection_success)

    def on_lifecycle_connection_failure(self, lifecycle_connection_failure: mqtt5.LifecycleConnectFailureData):
        self.last_exception = lifecycle_connection_failure.exception
        if self.future_connection_failure:
            if self.future_connection_failure.done():
                pass
            else:
                self.future_connection_failure.set_result(lifecycle_connection_failure)

    def on_lifecycle_disconnection(self, lifecycle_disconnect_data: mqtt5.LifecycleDisconnectData):
        if self.future_disconnection:
            self.future_disconnection.set_result(lifecycle_disconnect_data)


class Mqtt5ClientTest(NativeResourceTest):

    def _create_client(
            self,
            auth_type=AuthType.DIRECT,
            client_options: mqtt5.ClientOptions = None,
            callbacks: Mqtt5TestCallbacks = None):
        config = Config(auth_type)

        if client_options is None:
            client_options = mqtt5.ClientOptions(
                host_name=config.endpoint,
                port=int(config.port)
            )

        if client_options.connect_options is None:
            client_options.connect_options = mqtt5.ConnectPacket()
            client_options.connect_options.client_id = create_client_id()

        if (auth_type == AuthType.DIRECT or
            auth_type == AuthType.DIRECT_BASIC_AUTH or
            auth_type == AuthType.DIRECT_TLS or
            auth_type == AuthType.DIRECT_PROXY or
            auth_type == AuthType.WS or
            auth_type == AuthType.WS_BASIC_AUTH or
            auth_type == AuthType.WS_TLS or
            auth_type == AuthType.WS_PROXY or
            auth_type == AuthType.DIRECT_MUTUAL_TLS or
            auth_type == AuthType.DIRECT_BASIC_AUTH_BAD or
            auth_type == AuthType.DOUBLE_CLIENT_ID_FAILURE or
            auth_type == AuthType.DIRECT_HOST_ONLY or
            auth_type == AuthType.WS_BAD_PORT or
                auth_type == AuthType.DIRECT_HOST_AND_PORT_ONLY):
            client_options.host_name = config.endpoint

        if (auth_type == AuthType.DIRECT or
           auth_type == AuthType.DIRECT_BASIC_AUTH or
           auth_type == AuthType.DIRECT_TLS or
           auth_type == AuthType.DIRECT_PROXY or
           auth_type == AuthType.WS or
           auth_type == AuthType.WS_BASIC_AUTH or
           auth_type == AuthType.WS_TLS or
           auth_type == AuthType.WS_PROXY or
           auth_type == AuthType.DIRECT_MUTUAL_TLS or
           auth_type == AuthType.DIRECT_BASIC_AUTH_BAD or
           auth_type == AuthType.DOUBLE_CLIENT_ID_FAILURE or
           auth_type == AuthType.DIRECT_HOST_AND_PORT_ONLY):
            client_options.port = int(config.port)

        if auth_type == AuthType.DIRECT_BASIC_AUTH or auth_type == AuthType.WS_BASIC_AUTH:
            client_options.connect_options.username = config.username
            client_options.connect_options.password = config.password

        if (auth_type == AuthType.DIRECT_TLS or
                auth_type == AuthType.WS_TLS or
                auth_type == AuthType.DIRECT_PROXY):
            tls_ctx_options = io.TlsContextOptions()
            tls_ctx_options.verify_peer = False
            client_options.tls_ctx = io.ClientTlsContext(tls_ctx_options)

        if auth_type == AuthType.DIRECT_MUTUAL_TLS:
            tls_ctx_options = io.TlsContextOptions.create_client_with_mtls_from_path(config.cert_path, config.key_path)
            client_options.tls_ctx = io.ClientTlsContext(tls_ctx_options)

        if (auth_type == AuthType.WS or
                auth_type == AuthType.WS_BASIC_AUTH or
                auth_type == AuthType.WS_TLS or
                auth_type == AuthType.WS_PROXY or
                auth_type == AuthType.WS_BAD_PORT):
            client_options.websocket_handshake_transform = callbacks.ws_handshake_transform

        if auth_type == AuthType.DIRECT_PROXY or auth_type == AuthType.WS_PROXY:
            http_proxy_options = http.HttpProxyOptions(host_name=config.proxy_endpoint, port=int(config.proxy_port))
            http_proxy_options.connection_type = http.HttpProxyConnectionType.Tunneling
            http_proxy_options.auth_type = http.HttpProxyAuthenticationType.Nothing
            client_options.http_proxy_options = http_proxy_options

        if callbacks is not None:
            client_options.on_publish_callback_fn = callbacks.on_publish_received
            client_options.on_lifecycle_event_stopped_fn = callbacks.on_lifecycle_stopped
            client_options.on_lifecycle_event_attempting_connect_fn = callbacks.on_lifecycle_attempting_connect
            client_options.on_lifecycle_event_connection_success_fn = callbacks.on_lifecycle_connection_success
            client_options.on_lifecycle_event_connection_failure_fn = callbacks.on_lifecycle_connection_failure
            client_options.on_lifecycle_event_disconnection_fn = callbacks.on_lifecycle_disconnection

        client = mqtt5.Client(client_options)
        return client

    def _test_connect(self, auth_type=AuthType.DIRECT, client_options: mqtt5.ClientOptions = None):
        callbacks = Mqtt5TestCallbacks()
        client = self._create_client(auth_type=auth_type, callbacks=callbacks, client_options=client_options)
        client.start()
        callbacks.future_connection_success.result(TIMEOUT)
        return client, callbacks

    def _test_connect_fail(
            self,
            auth_type=AuthType.DIRECT,
            client_options: mqtt5.ClientOptions = None,
            expected_error_code: int = None):
        callbacks = Mqtt5TestCallbacks()
        client = self._create_client(auth_type=auth_type, callbacks=callbacks, client_options=client_options)
        client.start()
        callbacks.future_connection_failure.result(TIMEOUT)
        if (expected_error_code is not None):
            self.assertEqual(str(callbacks.last_exception), str(exceptions.from_code(expected_error_code)))
        return client, callbacks

    # ==============================================================
    #             CREATION TEST CASES
    # ==============================================================

    def test_client_creation_minimum(self):
        client = self._create_client()

    def test_client_creation_maximum(self):
        user_properties = []
        user_properties.append(mqtt5.UserProperty(name="name1", value="value1"))
        user_properties.append(mqtt5.UserProperty(name="name2", value="value2"))

        publish_packet = mqtt5.PublishPacket(
            payload="TEST_PAYLOAD",
            qos=mqtt5.QoS.AT_LEAST_ONCE,
            retain=False,
            topic="TEST_TOPIC",
            payload_format_indicator=mqtt5.PayloadFormatIndicator.AWS_MQTT5_PFI_UTF8,
            message_expiry_interval_sec=10,
            topic_alias=1,
            response_topic="TEST_RESPONSE_TOPIC",
            correlation_data="TEST_CORRELATION_DATA",
            content_type="TEST_CONTENT_TYPE",
            user_properties=user_properties
        )

        connect_options = mqtt5.ConnectPacket(
            keep_alive_interval_sec=10,
            client_id="TEST_CLIENT",
            username="USERNAME",
            password="PASSWORD",
            session_expiry_interval_sec=100,
            request_response_information=1,
            request_problem_information=1,
            receive_maximum=1000,
            maximum_packet_size=10000,
            will_delay_interval_sec=1000,
            will=publish_packet,
            user_properties=user_properties
        )
        client_options = mqtt5.ClientOptions(
            host_name="",
            port=0,
            connect_options=connect_options,
            session_behavior=mqtt5.ClientSessionBehaviorType.CLEAN,
            extended_validation_and_flow_control_options=mqtt5.ExtendedValidationAndFlowControlOptions.AWS_IOT_CORE_DEFAULTS,
            offline_queue_behavior=mqtt5.ClientOperationQueueBehaviorType.FAIL_ALL_ON_DISCONNECT,
            retry_jitter_mode=mqtt5.ExponentialBackoffJitterMode.DECORRELATED,
            min_reconnect_delay_ms=100,
            max_reconnect_delay_ms=50000,
            min_connected_time_to_reset_reconnect_delay_ms=1000,
            ping_timeout_ms=1000,
            connack_timeout_ms=1000,
            ack_timeout_sec=100)
        client = self._create_client(AuthType.DIRECT, client_options=client_options)

    # ==============================================================
    #             DIRECT CONNECT TEST CASES
    # ==============================================================

    def test_direct_connect_minimum(self):
        client, callbacks = self._test_connect(auth_type=AuthType.DIRECT)
        client.stop()
        callbacks.future_stopped.result(TIMEOUT)

    def test_direct_connect_basic_auth(self):
        client, callbacks = self._test_connect(auth_type=AuthType.DIRECT_BASIC_AUTH)
        client.stop()
        callbacks.future_stopped.result(TIMEOUT)

    def test_direct_connect_tls(self):
        client, callbacks = self._test_connect(auth_type=AuthType.DIRECT_TLS)
        client.stop()
        callbacks.future_stopped.result(TIMEOUT)

    def test_direct_connect_mutual_tls(self):
        client, callbacks = self._test_connect(auth_type=AuthType.DIRECT_MUTUAL_TLS)
        client.stop()
        callbacks.future_stopped.result(TIMEOUT)

    def test_direct_connect_http_proxy_tls(self):
        client_options = mqtt5.ClientOptions(
            host_name="",
            port=0,
            min_reconnect_delay_ms=100,
            max_reconnect_delay_ms=1000)
        client, callbacks = self._test_connect(auth_type=AuthType.DIRECT_PROXY, client_options=client_options)
        client.stop()
        callbacks.future_stopped.result(TIMEOUT)

    def test_direct_connect_maximum(self):
        user_properties = []
        user_properties.append(mqtt5.UserProperty(name="name1", value="value1"))
        user_properties.append(mqtt5.UserProperty(name="name2", value="value2"))

        publish_packet = mqtt5.PublishPacket(
            payload="TEST_PAYLOAD",
            qos=mqtt5.QoS.AT_LEAST_ONCE,
            retain=False,
            topic="TEST_TOPIC",
            payload_format_indicator=mqtt5.PayloadFormatIndicator.AWS_MQTT5_PFI_UTF8,
            message_expiry_interval_sec=10,
            topic_alias=1,
            response_topic="TEST_RESPONSE_TOPIC",
            correlation_data="TEST_CORRELATION_DATA",
            content_type="TEST_CONTENT_TYPE",
            user_properties=user_properties
        )

        connect_options = mqtt5.ConnectPacket(
            keep_alive_interval_sec=10,
            client_id="TEST_CLIENT",
            session_expiry_interval_sec=100,
            request_response_information=1,
            request_problem_information=1,
            receive_maximum=1000,
            maximum_packet_size=10000,
            will_delay_interval_sec=1000,
            will=publish_packet,
            user_properties=user_properties
        )
        client_options = mqtt5.ClientOptions(
            host_name="",
            port=0,
            connect_options=connect_options,
            session_behavior=mqtt5.ClientSessionBehaviorType.CLEAN,
            extended_validation_and_flow_control_options=mqtt5.ExtendedValidationAndFlowControlOptions.AWS_IOT_CORE_DEFAULTS,
            offline_queue_behavior=mqtt5.ClientOperationQueueBehaviorType.FAIL_ALL_ON_DISCONNECT,
            retry_jitter_mode=mqtt5.ExponentialBackoffJitterMode.DECORRELATED,
            min_reconnect_delay_ms=100,
            max_reconnect_delay_ms=50000,
            min_connected_time_to_reset_reconnect_delay_ms=1000,
            ping_timeout_ms=1000,
            connack_timeout_ms=1000,
            ack_timeout_sec=100)
        client, callbacks = self._test_connect(auth_type=AuthType.DIRECT, client_options=client_options)
        client.stop()
        callbacks.future_stopped.result(TIMEOUT)

    # ==============================================================
    #             WEBSOCKET CONNECT TEST CASES
    # ==============================================================

    def test_websocket_connect_minimum(self):
        client, callbacks = self._test_connect(auth_type=AuthType.WS)
        client.stop()
        callbacks.future_stopped.result(TIMEOUT)

    def test_websocket_connect_basic_auth(self):
        client, callbacks = self._test_connect(auth_type=AuthType.WS_BASIC_AUTH)
        client.stop()
        callbacks.future_stopped.result(TIMEOUT)

    def test_websocket_connect_tls(self):
        client, callbacks = self._test_connect(auth_type=AuthType.WS_TLS)
        client.stop()
        callbacks.future_stopped.result(TIMEOUT)

    # TODO test_websocket_connect_sigv4 against IoT Core

    # TODO can implement this later
    # def test_websocket_connect_http_proxy_tls(self):
    #     client, callbacks = self._test_connect(auth_type=AuthType.WS_PROXY)
    #     client.stop()
    #     callbacks.future_stopped.result(TIMEOUT)

    def test_websocket_connect_maximum(self):
        user_properties = []
        user_properties.append(mqtt5.UserProperty(name="name1", value="value1"))
        user_properties.append(mqtt5.UserProperty(name="name2", value="value2"))

        publish_packet = mqtt5.PublishPacket(
            payload="TEST_PAYLOAD",
            qos=mqtt5.QoS.AT_LEAST_ONCE,
            retain=False,
            topic="TEST_TOPIC",
            payload_format_indicator=mqtt5.PayloadFormatIndicator.AWS_MQTT5_PFI_UTF8,
            message_expiry_interval_sec=10,
            topic_alias=1,
            response_topic="TEST_RESPONSE_TOPIC",
            correlation_data="TEST_CORRELATION_DATA",
            content_type="TEST_CONTENT_TYPE",
            user_properties=user_properties
        )

        connect_options = mqtt5.ConnectPacket(
            keep_alive_interval_sec=10,
            client_id="TEST_CLIENT",
            session_expiry_interval_sec=100,
            request_response_information=1,
            request_problem_information=1,
            receive_maximum=1000,
            maximum_packet_size=10000,
            will_delay_interval_sec=1000,
            will=publish_packet,
            user_properties=user_properties
        )
        client_options = mqtt5.ClientOptions(
            host_name="",
            port=0,
            connect_options=connect_options,
            session_behavior=mqtt5.ClientSessionBehaviorType.CLEAN,
            extended_validation_and_flow_control_options=mqtt5.ExtendedValidationAndFlowControlOptions.AWS_IOT_CORE_DEFAULTS,
            offline_queue_behavior=mqtt5.ClientOperationQueueBehaviorType.FAIL_ALL_ON_DISCONNECT,
            retry_jitter_mode=mqtt5.ExponentialBackoffJitterMode.DECORRELATED,
            min_reconnect_delay_ms=100,
            max_reconnect_delay_ms=50000,
            min_connected_time_to_reset_reconnect_delay_ms=1000,
            ping_timeout_ms=1000,
            connack_timeout_ms=1000,
            ack_timeout_sec=100)
        client, callbacks = self._test_connect(auth_type=AuthType.WS, client_options=client_options)
        client.stop()
        callbacks.future_stopped.result(TIMEOUT)

    # ==============================================================
    #             NEGATIVE CONNECT TEST CASES
    # ==============================================================

    def test_connect_with_invalid_host_name(self):
        client_options = mqtt5.ClientOptions("badhost", 1883)
        client, callbacks = self._test_connect_fail(auth_type=AuthType.NO_APPLICATION, client_options=client_options)
        client.stop()
        callbacks.future_stopped.result(TIMEOUT)

    def test_connect_with_invalid_port(self):
        client_options = mqtt5.ClientOptions("will be set by _create_client", 444)
        client, callbacks = self._test_connect_fail(
            auth_type=AuthType.DIRECT_HOST_ONLY, client_options=client_options)
        client.stop()
        callbacks.future_stopped.result(TIMEOUT)

    def test_connect_with_invalid_port_for_websocket_connection(self):
        client_options = mqtt5.ClientOptions("will be set by _create_client", 1883)
        client, callbacks = self._test_connect_fail(
            auth_type=AuthType.WS_BAD_PORT, client_options=client_options)
        client.stop()
        callbacks.future_stopped.result(TIMEOUT)

    def test_connect_with_socket_timeout(self):
        client_options = mqtt5.ClientOptions("www.example.com", 81)
        client_options.connack_timeout_ms = 200
        client, callbacks = self._test_connect_fail(
            auth_type=AuthType.NO_APPLICATION, client_options=client_options)
        client.stop()
        callbacks.future_stopped.result(TIMEOUT)

    def test_connect_with_incorrect_basic_authentication_credentials(self):
        client_options = mqtt5.ClientOptions("will be set by _create_client", 0)
        client_options.connect_options = mqtt5.ConnectPacket(username="bad username", password="bad password")
        client, callbacks = self._test_connect_fail(
            auth_type=AuthType.DIRECT_BASIC_AUTH_BAD, client_options=client_options, expected_error_code=5150)
        client.stop()
        callbacks.future_stopped.result(TIMEOUT)

    # TODO test_websocket_handshake_failure

    def test_double_client_id_failure(self):
        shared_client_id = create_client_id()

        callbacks = Mqtt5TestCallbacks()
        client_options = mqtt5.ClientOptions("will be set by _create_client", 0)
        client_options.connect_options = mqtt5.ConnectPacket(client_id=shared_client_id)
        client1 = self._create_client(
            AuthType.DOUBLE_CLIENT_ID_FAILURE,
            client_options=client_options,
            callbacks=callbacks)

        callbacks2 = Mqtt5TestCallbacks()
        client_options2 = mqtt5.ClientOptions("will be set by _create_client", 0)
        client_options2.connect_options = mqtt5.ConnectPacket(client_id=shared_client_id)
        client2 = Mqtt5ClientTest._create_client(
            AuthType.DOUBLE_CLIENT_ID_FAILURE,
            client_options=client_options2,
            callbacks=callbacks2)

        client1.start()
        callbacks.future_connection_success.result(TIMEOUT)

        client2.start()

        callbacks.future_disconnection.result(TIMEOUT)

        client1.stop()
        callbacks.future_stopped.result(TIMEOUT)
        client2.stop()
        callbacks2.future_stopped.result(TIMEOUT)

    # ==============================================================
    #             NEGATIVE DATA INPUT TEST CASES
    # ==============================================================

    def test_negative_connect_packet_properties(self):

        connect_options = mqtt5.ConnectPacket(
            keep_alive_interval_sec=-10,
        )

        client_options = mqtt5.ClientOptions(
            host_name="",
            port=0,
            connect_options=connect_options,
        )

        with self.assertRaises(OverflowError) as cm:
            self._create_client(AuthType.DIRECT_HOST_AND_PORT_ONLY, client_options=client_options)

        connect_options = mqtt5.ConnectPacket(
            session_expiry_interval_sec=-100,
        )

        client_options = mqtt5.ClientOptions(
            host_name="",
            port=0,
            connect_options=connect_options,
        )

        with self.assertRaises(OverflowError) as cm:
            self._create_client(AuthType.DIRECT_HOST_AND_PORT_ONLY, client_options=client_options)

        connect_options = mqtt5.ConnectPacket(
            receive_maximum=-1000,
        )

        client_options = mqtt5.ClientOptions(
            host_name="",
            port=0,
            connect_options=connect_options,
        )

        with self.assertRaises(OverflowError) as cm:
            self._create_client(AuthType.DIRECT_HOST_AND_PORT_ONLY, client_options=client_options)

        connect_options = mqtt5.ConnectPacket(
            maximum_packet_size=-10000,
        )

        client_options = mqtt5.ClientOptions(
            host_name="",
            port=0,
            connect_options=connect_options,
        )

        with self.assertRaises(OverflowError) as cm:
            self._create_client(AuthType.DIRECT_HOST_AND_PORT_ONLY, client_options=client_options)

        connect_options = mqtt5.ConnectPacket(
            will_delay_interval_sec=-1000,
        )

        client_options = mqtt5.ClientOptions(
            host_name="",
            port=0,
            connect_options=connect_options,
        )

        with self.assertRaises(OverflowError) as cm:
            self._create_client(AuthType.DIRECT_HOST_AND_PORT_ONLY, client_options=client_options)

    def test_overflow_connect_packet_properties(self):

        connect_options = mqtt5.ConnectPacket(
            keep_alive_interval_sec=65536
        )

        client_options = mqtt5.ClientOptions(
            host_name="",
            port=0,
            connect_options=connect_options,
        )

        with self.assertRaises(OverflowError) as cm:
            self._create_client(AuthType.DIRECT_HOST_AND_PORT_ONLY, client_options=client_options)

        connect_options = mqtt5.ConnectPacket(
            session_expiry_interval_sec=4294967296
        )

        client_options = mqtt5.ClientOptions(
            host_name="",
            port=0,
            connect_options=connect_options,
        )

        with self.assertRaises(OverflowError) as cm:
            self._create_client(AuthType.DIRECT_HOST_AND_PORT_ONLY, client_options=client_options)

        connect_options = mqtt5.ConnectPacket(
            receive_maximum=65536
        )

        client_options = mqtt5.ClientOptions(
            host_name="",
            port=0,
            connect_options=connect_options,
        )

        with self.assertRaises(OverflowError) as cm:
            self._create_client(AuthType.DIRECT_HOST_AND_PORT_ONLY, client_options=client_options)

        connect_options = mqtt5.ConnectPacket(
            maximum_packet_size=4294967296
        )

        client_options = mqtt5.ClientOptions(
            host_name="",
            port=0,
            connect_options=connect_options,
        )

        with self.assertRaises(OverflowError) as cm:
            self._create_client(AuthType.DIRECT_HOST_AND_PORT_ONLY, client_options=client_options)

        connect_options = mqtt5.ConnectPacket(
            will_delay_interval_sec=4294967296
        )

        client_options = mqtt5.ClientOptions(
            host_name="",
            port=0,
            connect_options=connect_options,
        )

        with self.assertRaises(OverflowError) as cm:
            self._create_client(AuthType.DIRECT_HOST_AND_PORT_ONLY, client_options=client_options)

    def test_negative_disconnect_packet_properties(self):

        client, callbacks = self._test_connect(auth_type=AuthType.DIRECT)

        disconnect_packet = mqtt5.DisconnectPacket(session_expiry_interval_sec=-1)

        with self.assertRaises(OverflowError) as cm:
            client.stop(disconnect_packet=disconnect_packet)

        client.stop()
        callbacks.future_stopped.result(TIMEOUT)

    def test_negative_publish_packet_properties(self):

        client, callbacks = self._test_connect(auth_type=AuthType.DIRECT)

        publish_packet = mqtt5.PublishPacket(message_expiry_interval_sec=-1)
        with self.assertRaises(OverflowError) as cm:
            client.publish(publish_packet=publish_packet)

        client.stop()
        callbacks.future_stopped.result(TIMEOUT)

    def test_negative_subscribe_packet_properties(self):

        client, callbacks = self._test_connect(auth_type=AuthType.DIRECT)

        subscriptions = []
        subscriptions.append(mqtt5.Subscription(topic_filter="test1", qos=mqtt5.QoS.AT_LEAST_ONCE))
        subscribe_packet = mqtt5.SubscribePacket(subscription_identifier=-1, subscriptions=subscriptions)

        with self.assertRaises(OverflowError) as cm:
            client.subscribe(subscribe_packet=subscribe_packet)

        client.stop()
        callbacks.future_stopped.result(TIMEOUT)

    # ==============================================================
    #             NEGOTIATED SETTINGS TEST CASES
    # ==============================================================

    def test_negotiated_settings_minimal_settings(self):

        connect_options = mqtt5.ConnectPacket(
            session_expiry_interval_sec=600000
        )
        client_options = mqtt5.ClientOptions(
            host_name="to be set",
            port=0,
            connect_options=connect_options)

        client, callbacks = self._test_connect(auth_type=AuthType.DIRECT, client_options=client_options)

        self.assertIsNotNone(callbacks.negotiated_settings)
        self.assertEqual(callbacks.negotiated_settings.session_expiry_interval_sec, 600000)

        client.stop()
        callbacks.future_stopped.result(TIMEOUT)

    def test_negotiated_settings_maximum_settings(self):

        client_id = create_client_id()
        connect_options = mqtt5.ConnectPacket(
            client_id=client_id,
            session_expiry_interval_sec=600,
            keep_alive_interval_sec=1000
        )

        client_options = mqtt5.ClientOptions(
            host_name="to be set",
            port=0,
            connect_options=connect_options)

        client, callbacks = self._test_connect(auth_type=AuthType.DIRECT, client_options=client_options)

        self.assertIsNotNone(callbacks.negotiated_settings)
        self.assertIsNotNone(callbacks.connack_packet)
        self.assertIsNone(callbacks.connack_packet.assigned_client_identifier)
        self.assertEqual(callbacks.negotiated_settings.session_expiry_interval_sec, 600)
        self.assertEqual(callbacks.negotiated_settings.server_keep_alive_sec, 1000)
        self.assertEqual(callbacks.negotiated_settings.maximum_qos, mqtt5.QoS.AT_LEAST_ONCE)
        self.assertEqual(callbacks.negotiated_settings.receive_maximum_from_server, 10)
        self.assertEqual(callbacks.negotiated_settings.maximum_packet_size_to_server, 268435460)
        self.assertEqual(callbacks.negotiated_settings.topic_alias_maximum_to_server, 10)
        self.assertEqual(callbacks.negotiated_settings.topic_alias_maximum_to_client, 0)
        self.assertTrue(callbacks.negotiated_settings.retain_available)
        self.assertTrue(callbacks.negotiated_settings.wildcard_subscriptions_available)
        self.assertTrue(callbacks.negotiated_settings.subscription_identifiers_available)
        self.assertTrue(callbacks.negotiated_settings.shared_subscriptions_available)
        self.assertFalse(callbacks.negotiated_settings.rejoined_session)

        client.stop()
        callbacks.future_stopped.result(TIMEOUT)

    def test_negotiated_settings_server_limit(self):

        uint32_max = 4294967295
        uint16_max = 65535

        connect_options = mqtt5.ConnectPacket(
            session_expiry_interval_sec=uint32_max,
            receive_maximum=uint16_max,
            keep_alive_interval_sec=uint16_max,
            maximum_packet_size=uint32_max
        )

        client_options = mqtt5.ClientOptions(
            host_name="to be set",
            port=0,
            connect_options=connect_options)

        client, callbacks = self._test_connect(auth_type=AuthType.DIRECT, client_options=client_options)

        self.assertIsNotNone(callbacks.negotiated_settings)
        self.assertNotEqual(callbacks.negotiated_settings.receive_maximum_from_server, uint16_max)
        self.assertNotEqual(callbacks.negotiated_settings.maximum_packet_size_to_server, uint32_max)
        self.assertEqual(callbacks.negotiated_settings.server_keep_alive_sec, uint16_max)
        self.assertEqual(callbacks.negotiated_settings.session_expiry_interval_sec, uint32_max)

        client.stop()
        callbacks.future_stopped.result(TIMEOUT)

    # ==============================================================
    #             OPERATION TEST CASES
    # ==============================================================

    def test_operation_sub_unsub(self):

        client_id = create_client_id()
        topic_filter = "test/MQTT5_Binding_Python_" + client_id
        payload = "Hello World"

        client, callbacks = self._test_connect(auth_type=AuthType.DIRECT_MUTUAL_TLS)
        callbacks.on_publish_receive_expected = 1

        subscriptions = []
        subscriptions.append(mqtt5.Subscription(topic_filter=topic_filter, qos=mqtt5.QoS.AT_LEAST_ONCE))
        subscribe_packet = mqtt5.SubscribePacket(
            subscriptions=subscriptions)
        subscribe_future = client.subscribe(subscribe_packet=subscribe_packet)
        suback_packet = subscribe_future.result(TIMEOUT)
        self.assertIsInstance(suback_packet, mqtt5.SubackPacket)

        publish_packet = mqtt5.PublishPacket(
            payload=payload,
            topic=topic_filter,
            qos=mqtt5.QoS.AT_LEAST_ONCE)

        publish_future = client.publish(publish_packet=publish_packet)
        publish_completion_data = publish_future.result(TIMEOUT)
        puback_packet = publish_completion_data.puback
        self.assertIsInstance(puback_packet, mqtt5.PubackPacket)

        callbacks.future_expected_publishes_received.result(TIMEOUT)

        topic_filters = []
        topic_filters.append(topic_filter)
        unsubscribe_packet = mqtt5.UnsubscribePacket(topic_filters=topic_filters)
        unsubscribe_future = client.unsubscribe(unsubscribe_packet)
        unsuback_packet = unsubscribe_future.result(TIMEOUT)
        self.assertIsInstance(unsuback_packet, mqtt5.UnsubackPacket)

        publish_future = client.publish(publish_packet=publish_packet)
        publish_completion_data = publish_future.result(TIMEOUT)
        puback_packet = publish_completion_data.puback
        self.assertIsInstance(puback_packet, mqtt5.PubackPacket)

        self.assertEqual(callbacks.on_publish_received_counter, 1)

        client.stop()
        callbacks.future_stopped.result(TIMEOUT)

    def test_operation_will(self):
        client_id_publisher = create_client_id()
        topic_filter = "test/MQTT5_Binding_Python_" + client_id_publisher

        will_packet = mqtt5.PublishPacket(
            payload="TEST WILL",
            qos=mqtt5.QoS.AT_LEAST_ONCE,
            topic=topic_filter
        )
        client_options1 = mqtt5.ClientOptions("will be replaced", 0)
        client_options1.connect_options = mqtt5.ConnectPacket(client_id=client_id_publisher,
                                                              will_delay_interval_sec=0,
                                                              will=will_packet)
        client1, callbacks1 = self._test_connect(auth_type=AuthType.DIRECT, client_options=client_options1)

        client_id_subscriber = create_client_id()
        client_options2 = mqtt5.ClientOptions("will be replaced", 0)
        client_options2.connect_options = mqtt5.ConnectPacket(client_id=client_id_subscriber)
        client2, callbacks2 = self._test_connect(auth_type=AuthType.DIRECT, client_options=client_options2)

        subscriptions = []
        subscriptions.append(mqtt5.Subscription(topic_filter=topic_filter, qos=mqtt5.QoS.AT_LEAST_ONCE))
        subscribe_packet = mqtt5.SubscribePacket(
            subscriptions=subscriptions)
        subscribe_future = client2.subscribe(subscribe_packet=subscribe_packet)
        suback_packet = subscribe_future.result(TIMEOUT)
        self.assertIsInstance(suback_packet, mqtt5.SubackPacket)

        disconnect_packet = mqtt5.DisconnectPacket(reason_code=mqtt5.DisconnectReasonCode.DISCONNECT_WITH_WILL_MESSAGE)
        client1.stop(disconnect_packet=disconnect_packet)
        callbacks1.future_stopped.result(TIMEOUT)

        received_will = callbacks2.future_publish_received.result(TIMEOUT)
        self.assertIsInstance(received_will, mqtt5.PublishPacket)
        client2.stop()
        callbacks2.future_stopped.result(TIMEOUT)

    def test_operation_binary_publish(self):

        client_id = create_client_id()
        topic_filter = "test/MQTT5_Binding_Python_" + client_id
        payload = bytearray(os.urandom(256))

        client, callbacks = self._test_connect(auth_type=AuthType.DIRECT_MUTUAL_TLS)

        subscriptions = []
        subscriptions.append(mqtt5.Subscription(topic_filter=topic_filter, qos=mqtt5.QoS.AT_LEAST_ONCE))
        subscribe_packet = mqtt5.SubscribePacket(
            subscriptions=subscriptions)
        subscribe_future = client.subscribe(subscribe_packet=subscribe_packet)
        suback_packet = subscribe_future.result(TIMEOUT)
        self.assertIsInstance(suback_packet, mqtt5.SubackPacket)

        publish_packet = mqtt5.PublishPacket(
            payload=payload,
            topic=topic_filter,
            qos=mqtt5.QoS.AT_LEAST_ONCE)

        publish_future = client.publish(publish_packet=publish_packet)
        publish_completion_data = publish_future.result(TIMEOUT)
        puback_packet = publish_completion_data.puback
        self.assertIsInstance(puback_packet, mqtt5.PubackPacket)

        received_publish = callbacks.future_publish_received.result(TIMEOUT)
        self.assertIsInstance(received_publish, mqtt5.PublishPacket)
        self.assertEqual(received_publish.payload, payload)

        topic_filters = []
        topic_filters.append(topic_filter)
        unsubscribe_packet = mqtt5.UnsubscribePacket(topic_filters=topic_filters)
        unsubscribe_future = client.unsubscribe(unsubscribe_packet)
        unsuback_packet = unsubscribe_future.result(TIMEOUT)
        self.assertIsInstance(unsuback_packet, mqtt5.UnsubackPacket)

        publish_future = client.publish(publish_packet=publish_packet)
        publish_completion_data = publish_future.result(TIMEOUT)
        puback_packet = publish_completion_data.puback
        self.assertIsInstance(puback_packet, mqtt5.PubackPacket)

        self.assertEqual(callbacks.on_publish_received_counter, 1)

        client.stop()
        callbacks.future_stopped.result(TIMEOUT)

    # ==============================================================
    #             OPERATION ERROR TEST CASES
    # ==============================================================

    def test_operation_error_null_publish(self):

        client, callbacks = self._test_connect(auth_type=AuthType.DIRECT)

        with self.assertRaises(Exception) as cm:
            client.publish(None)

        client.stop()
        callbacks.future_stopped.result(TIMEOUT)

    def test_operation_error_null_subscribe(self):

        client, callbacks = self._test_connect(auth_type=AuthType.DIRECT)

        with self.assertRaises(Exception) as cm:
            client.subscribe(None)

        client.stop()
        callbacks.future_stopped.result(TIMEOUT)

    def test_operation_error_null_unsubscribe(self):

        client, callbacks = self._test_connect(auth_type=AuthType.DIRECT)

        with self.assertRaises(Exception) as cm:
            client.unsubscribe(None)

        client.stop()
        callbacks.future_stopped.result(TIMEOUT)

    def test_operation_rejoin_always(self):
        client_id = create_client_id()

        client_options = mqtt5.ClientOptions(
            "will be replaced", 0, session_behavior=mqtt5.ClientSessionBehaviorType.REJOIN_ALWAYS)
        client_options.connect_options = mqtt5.ConnectPacket(
            client_id=client_id, session_expiry_interval_sec=3600, keep_alive_interval_sec=360)

        client1, callbacks1 = self._test_connect(auth_type=AuthType.DIRECT_MUTUAL_TLS, client_options=client_options)
        client1.stop()
        callbacks1.future_stopped.result(TIMEOUT)

        callbacks2 = Mqtt5TestCallbacks()
        client2 = self._create_client(
            auth_type=AuthType.DIRECT_MUTUAL_TLS,
            client_options=client_options,
            callbacks=callbacks2)
        client2.start()
        connection_success_data = callbacks2.future_connection_success.result(TIMEOUT)
        connack_packet = connection_success_data.connack_packet
        self.assertTrue(connack_packet.session_present)
        client2.stop()
        callbacks2.future_stopped.result(TIMEOUT)

    # ==============================================================
    #             QOS1 TEST CASES
    # ==============================================================

    def test_qos1_happy_path(self):
        client_id_publisher = create_client_id()
        payload = "HELLO WORLD"
        topic_filter = "test/MQTT5_Binding_Python_" + client_id_publisher

        client_options = mqtt5.ClientOptions("will be replaced", 0)
        client_options.connect_options = mqtt5.ConnectPacket(client_id=client_id_publisher)
        client1, callbacks = self._test_connect(auth_type=AuthType.DIRECT_MUTUAL_TLS, client_options=client_options)

        client_id_subscriber = create_client_id()
        client_options2 = mqtt5.ClientOptions("will be replaced", 0)
        client_options2.connect_options = mqtt5.ConnectPacket(client_id=client_id_subscriber)
        client2, callbacks2 = self._test_connect(auth_type=AuthType.DIRECT_MUTUAL_TLS, client_options=client_options2)
        callbacks2.on_publish_receive_expected = 10

        subscriptions = []
        subscriptions.append(mqtt5.Subscription(topic_filter=topic_filter, qos=mqtt5.QoS.AT_LEAST_ONCE))
        subscribe_packet = mqtt5.SubscribePacket(
            subscriptions=subscriptions)
        subscribe_future = client2.subscribe(subscribe_packet=subscribe_packet)
        suback_packet = subscribe_future.result(TIMEOUT)
        self.assertIsInstance(suback_packet, mqtt5.SubackPacket)

        publishes = 10

        publish_packet = mqtt5.PublishPacket(
            payload=payload,
            topic=topic_filter,
            qos=mqtt5.QoS.AT_LEAST_ONCE)

        for x in range(publishes):
            publish_future = client1.publish(publish_packet)
            publish_future.result(TIMEOUT)

        client1.stop()
        callbacks.future_stopped.result(TIMEOUT)

        callbacks2.future_expected_publishes_received.result(TIMEOUT)
        self.assertEqual(callbacks2.on_publish_received_counter, publishes)

        client2.stop()
        callbacks2.future_stopped.result(TIMEOUT)

    # ==============================================================
    #             RETAIN TEST CASES
    # ==============================================================

    def test_retain_set_and_clear(self):
        client_id_publisher = create_client_id()
        payload = "HELLO WORLD"
        topic_filter = "test/MQTT5_Binding_Python_" + client_id_publisher
        callbacks = Mqtt5TestCallbacks()
        client_options = mqtt5.ClientOptions("will be replaced", 0)
        client_options.connect_options = mqtt5.ConnectPacket(client_id=client_id_publisher)
        client1 = self._create_client(AuthType.DIRECT, client_options=client_options, callbacks=callbacks)
        client1.start()
        callbacks.future_connection_success.result(TIMEOUT)

        publish_packet = mqtt5.PublishPacket(
            payload=payload,
            topic=topic_filter,
            retain=True,
            qos=mqtt5.QoS.AT_LEAST_ONCE)
        puback_future1 = client1.publish(publish_packet)
        puback_future1.result(TIMEOUT)

        client_id_subscriber = create_client_id()
        callbacks2 = Mqtt5TestCallbacks()
        client_options2 = mqtt5.ClientOptions("will be replaced", 0)
        client_options2.connect_options = mqtt5.ConnectPacket(client_id=client_id_subscriber)
        client2 = Mqtt5ClientTest._create_client(AuthType.DIRECT, client_options=client_options2, callbacks=callbacks2)
        client2.start()
        callbacks2.future_connection_success.result(TIMEOUT)

        subscriptions = []
        subscriptions.append(mqtt5.Subscription(topic_filter=topic_filter, qos=mqtt5.QoS.AT_LEAST_ONCE))
        subscribe_packet = mqtt5.SubscribePacket(
            subscriptions=subscriptions)
        subscribe_future1 = client2.subscribe(subscribe_packet=subscribe_packet)
        suback_packet1 = subscribe_future1.result(TIMEOUT)
        self.assertIsInstance(suback_packet1, mqtt5.SubackPacket)

        received_retained_publish1 = callbacks2.future_publish_received.result(TIMEOUT)
        self.assertIsInstance(received_retained_publish1, mqtt5.PublishPacket)
        client2.stop()
        callbacks2.future_stopped.result(TIMEOUT)

        publish_packet.payload = None
        puback_future2 = client1.publish(publish_packet)
        puback_future2.result(TIMEOUT)

        client1.stop()
        callbacks.future_stopped.result(TIMEOUT)

        client_id_subscriber2 = create_client_id()
        callbacks3 = Mqtt5TestCallbacks()
        client_options3 = mqtt5.ClientOptions("will be replaced", 0)
        client_options3.connect_options = mqtt5.ConnectPacket(client_id=client_id_subscriber2)
        client3 = Mqtt5ClientTest._create_client(AuthType.DIRECT, client_options=client_options3, callbacks=callbacks3)
        client3.start()
        callbacks3.future_connection_success.result(TIMEOUT)

        subscribe_future2 = client3.subscribe(subscribe_packet=subscribe_packet)
        suback_packet2 = subscribe_future2.result(TIMEOUT)
        self.assertIsInstance(suback_packet2, mqtt5.SubackPacket)

        time.sleep(1)
        self.assertEqual(callbacks3.on_publish_received_counter, 0)

        client3.stop()
        callbacks3.future_stopped.result(TIMEOUT)

    # ==============================================================
    #             INTERRUPTION TEST CASES
    # ==============================================================

    def test_interruption_sub(self):

        client_id = create_client_id()
        topic_filter = "test/MQTT5_Binding_Python_" + client_id
        callbacks = Mqtt5TestCallbacks()
        client = self._create_client(auth_type=AuthType.DIRECT_MUTUAL_TLS, callbacks=callbacks)
        client.start()
        callbacks.future_connection_success.result(TIMEOUT)

        subscriptions = []
        subscriptions.append(mqtt5.Subscription(topic_filter=topic_filter, qos=mqtt5.QoS.AT_LEAST_ONCE))
        subscribe_packet = mqtt5.SubscribePacket(
            subscriptions=subscriptions)
        subscribe_future = client.subscribe(subscribe_packet=subscribe_packet)
        client.stop()

        with self.assertRaises(Exception):
            subscribe_future.result(TIMEOUT)

        callbacks.future_stopped.result(TIMEOUT)

    def test_interruption_unsub(self):
        client_id = create_client_id()
        topic_filter = "test/MQTT5_Binding_Python_" + client_id
        callbacks = Mqtt5TestCallbacks()
        client = self._create_client(auth_type=AuthType.DIRECT_MUTUAL_TLS, callbacks=callbacks)
        client.start()
        callbacks.future_connection_success.result(TIMEOUT)

        topic_filters = []
        topic_filters.append(topic_filter)
        unsubscribe_packet = mqtt5.UnsubscribePacket(topic_filters=topic_filters)
        unsubscribe_future = client.unsubscribe(unsubscribe_packet)
        client.stop()

        with self.assertRaises(Exception):
            unsubscribe_future.result(TIMEOUT)

        callbacks.future_stopped.result(TIMEOUT)

    def test_interruption_qos1_publish(self):
        client_id = create_client_id()
        topic_filter = "test/MQTT5_Binding_Python_" + client_id
        payload = "test payload"
        callbacks = Mqtt5TestCallbacks()
        client = self._create_client(auth_type=AuthType.DIRECT_MUTUAL_TLS, callbacks=callbacks)
        client.start()
        callbacks.future_connection_success.result(TIMEOUT)

        publish_packet = mqtt5.PublishPacket(
            payload=payload,
            topic=topic_filter,
            qos=mqtt5.QoS.AT_LEAST_ONCE)

        publish_future = client.publish(publish_packet=publish_packet)
        client.stop()

        with self.assertRaises(Exception):
            publish_future.result(TIMEOUT)

        callbacks.future_stopped.result(TIMEOUT)

    # ==============================================================
    #             MISC TEST CASES
    # ==============================================================

    def test_operation_statistics_uc1(self):
        client_id_publisher = create_client_id()
        payload = "HELLO WORLD"
        topic_filter = "test/MQTT5_Binding_Python_" + client_id_publisher

        client_options = mqtt5.ClientOptions("will be replaced", 0)
        client_options.connect_options = mqtt5.ConnectPacket(client_id=client_id_publisher)
        client1, callbacks = self._test_connect(auth_type=AuthType.DIRECT_MUTUAL_TLS, client_options=client_options)

        # Make sure the operation statistics are empty
        statistics = client1.get_stats()
        self.assertEqual(statistics.incomplete_operation_count, 0)
        self.assertEqual(statistics.incomplete_operation_size, 0)
        self.assertEqual(statistics.unacked_operation_count, 0)
        self.assertEqual(statistics.unacked_operation_size, 0)

        publish_packet = mqtt5.PublishPacket(
            payload=payload,
            topic=topic_filter,
            qos=mqtt5.QoS.AT_LEAST_ONCE)

        publishes = 10
        for x in range(publishes):
            publish_future = client1.publish(publish_packet)
            publish_future.result(TIMEOUT)

        # Make sure the operation statistics are empty
        statistics = client1.get_stats()
        self.assertEqual(statistics.incomplete_operation_count, 0)
        self.assertEqual(statistics.incomplete_operation_size, 0)
        self.assertEqual(statistics.unacked_operation_count, 0)
        self.assertEqual(statistics.unacked_operation_size, 0)

        client1.stop()
        callbacks.future_stopped.result(TIMEOUT)


if __name__ == 'main':
    unittest.main()
