import pytest
from aws_cdk import App, Environment
from aws_cdk.assertions import Template
from infrastructure.lib.security.siem_sinks_stack import (
    SiemSinksStack,
    SiemSinksFactory,
    OpenSearchSink,
    SplunkSink,
    ElasticSink,
)
from infrastructure.lib.security.security_lake_stack import SecurityLakeStack


class TestSiemSinksStack:
    """Test suite for the SiemSinksStack."""

    def create_security_lake_stack(self, app: App) -> SecurityLakeStack:
        """Helper method to create a SecurityLakeStack for testing."""
        return SecurityLakeStack(
            app,
            "test-security-lake",
            primary_region="us-east-1",
            secondary_region="us-west-2",
            security_admin_account_id="111111111111",
            env=Environment(account="123456789012", region="us-east-1"),
        )

    def test_siem_sinks_factory_opensearch(self):
        """Test that the factory creates an OpenSearch sink correctly."""
        # Given
        app = App(context={"sinkType": "opensearch"})
        security_lake_stack = self.create_security_lake_stack(app)

        # When
        stack = SiemSinksStack(
            app,
            "test-siem-sinks",
            security_lake_stack=security_lake_stack,
            env=Environment(account="123456789012", region="us-east-1"),
        )

        # Then
        assert isinstance(stack, SiemSinksStack)

    def test_siem_sinks_factory_splunk(self):
        """Test that the factory creates a Splunk sink correctly."""
        # Given
        app = App(context={"sinkType": "splunk"})
        security_lake_stack = self.create_security_lake_stack(app)

        # When
        stack = SiemSinksStack(
            app,
            "test-siem-sinks",
            security_lake_stack=security_lake_stack,
            env=Environment(account="123456789012", region="us-east-1"),
        )

        # Then
        assert isinstance(stack, SiemSinksStack)

    def test_siem_sinks_factory_elastic(self):
        """Test that the factory creates an Elastic sink correctly."""
        # Given
        app = App(context={"sinkType": "elastic"})
        security_lake_stack = self.create_security_lake_stack(app)

        # When
        stack = SiemSinksStack(
            app,
            "test-siem-sinks",
            security_lake_stack=security_lake_stack,
            env=Environment(account="123456789012", region="us-east-1"),
        )

        # Then
        assert isinstance(stack, SiemSinksStack)

    def test_siem_sinks_factory_invalid_type(self):
        """Test that the factory raises an error for invalid sink type."""
        # Given
        app = App(context={"sinkType": "invalid"})
        security_lake_stack = self.create_security_lake_stack(app)

        # When/Then
        with pytest.raises(ValueError, match="Unsupported SIEM sink type: invalid"):
            SiemSinksStack(
                app,
                "test-siem-sinks",
                security_lake_stack=security_lake_stack,
                env=Environment(account="123456789012", region="us-east-1"),
            )


class TestOpenSearchSink:
    """Test suite for the OpenSearchSink."""

    def test_opensearch_sink_resources_created(self):
        """Test that OpenSearch sink creates the correct resources."""
        # Given
        app = App()
        security_lake_stack = SecurityLakeStack(
            app,
            "test-security-lake",
            primary_region="us-east-1",
            secondary_region="us-west-2",
            security_admin_account_id="111111111111",
            env=Environment(account="123456789012", region="us-east-1"),
        )

        # When
        sink = OpenSearchSink(app, "OpenSearchTest", security_lake_stack)
        sink.create_sink()

        # Then
        template = Template.from_stack(app)
        template.has_resource_properties(
            "AWS::OpenSearchServerless::Collection",
            {"Name": "security-lake-collection", "Type": "TIMESERIES"},
        )

        # Check that the subscriber is created
        template.has_resource_properties(
            "AWS::SecurityLake::Subscriber",
            {"SubscriberName": "OpenSearchServerlessSubscriber", "AccessTypes": ["S3"]},
        )

    def test_opensearch_sink_outputs(self):
        """Test that OpenSearch sink creates outputs."""
        # Given
        app = App()
        security_lake_stack = SecurityLakeStack(
            app,
            "test-security-lake",
            primary_region="us-east-1",
            secondary_region="us-west-2",
            security_admin_account_id="111111111111",
            env=Environment(account="123456789012", region="us-east-1"),
        )

        # When
        sink = OpenSearchSink(app, "OpenSearchTest", security_lake_stack)
        sink.create_sink()

        # Then
        template = Template.from_stack(app)
        template.has_output("OpenSearchCollectionEndpoint", {})


class TestSplunkSink:
    """Test suite for the SplunkSink."""

    def test_splunk_sink_resources_created(self):
        """Test that Splunk sink creates the correct resources."""
        # Given
        app = App()
        security_lake_stack = SecurityLakeStack(
            app,
            "test-security-lake",
            primary_region="us-east-1",
            secondary_region="us-west-2",
            security_admin_account_id="111111111111",
            env=Environment(account="123456789012", region="us-east-1"),
        )

        # When
        sink = SplunkSink(app, "SplunkTest", security_lake_stack)
        sink.create_sink()

        # Then
        template = Template.from_stack(app)
        template.has_resource_properties(
            "AWS::KinesisFirehose::DeliveryStream",
            {
                "DeliveryStreamType": "DirectPut",
                "SplunkDestinationConfiguration": {"HECEndpointType": "Raw"},
            },
        )

    def test_splunk_sink_outputs(self):
        """Test that Splunk sink creates outputs."""
        # Given
        app = App()
        security_lake_stack = SecurityLakeStack(
            app,
            "test-security-lake",
            primary_region="us-east-1",
            secondary_region="us-west-2",
            security_admin_account_id="111111111111",
            env=Environment(account="123456789012", region="us-east-1"),
        )

        # When
        sink = SplunkSink(app, "SplunkTest", security_lake_stack)
        sink.create_sink()

        # Then
        template = Template.from_stack(app)
        template.has_output("SplunkDeliveryStreamName", {})


class TestElasticSink:
    """Test suite for the ElasticSink."""

    def test_elastic_sink_resources_created(self):
        """Test that Elastic sink creates the correct resources."""
        # Given
        app = App()
        security_lake_stack = SecurityLakeStack(
            app,
            "test-security-lake",
            primary_region="us-east-1",
            secondary_region="us-west-2",
            security_admin_account_id="111111111111",
            env=Environment(account="123456789012", region="us-east-1"),
        )

        # When
        sink = ElasticSink(app, "ElasticTest", security_lake_stack)
        sink.create_sink()

        # Then
        template = Template.from_stack(app)
        template.has_resource_properties(
            "AWS::KinesisFirehose::DeliveryStream",
            {
                "DeliveryStreamType": "DirectPut",
                "HttpEndpointDestinationConfiguration": {},
            },
        )

    def test_elastic_sink_outputs(self):
        """Test that Elastic sink creates outputs."""
        # Given
        app = App()
        security_lake_stack = SecurityLakeStack(
            app,
            "test-security-lake",
            primary_region="us-east-1",
            secondary_region="us-west-2",
            security_admin_account_id="111111111111",
            env=Environment(account="123456789012", region="us-east-1"),
        )

        # When
        sink = ElasticSink(app, "ElasticTest", security_lake_stack)
        sink.create_sink()

        # Then
        template = Template.from_stack(app)
        template.has_output("ElasticDeliveryStreamName", {})


class TestSiemSinksFactory:
    """Test suite for the SiemSinksFactory."""

    def test_create_opensearch_sink(self):
        """Test that factory creates OpenSearch sink."""
        # Given
        app = App()
        security_lake_stack = SecurityLakeStack(
            app,
            "test-security-lake",
            primary_region="us-east-1",
            secondary_region="us-west-2",
            security_admin_account_id="111111111111",
            env=Environment(account="123456789012", region="us-east-1"),
        )
        factory = SiemSinksFactory(app, security_lake_stack)

        # When
        sink = factory.create_sink("opensearch")

        # Then
        assert isinstance(sink, OpenSearchSink)

    def test_create_splunk_sink(self):
        """Test that factory creates Splunk sink."""
        # Given
        app = App()
        security_lake_stack = SecurityLakeStack(
            app,
            "test-security-lake",
            primary_region="us-east-1",
            secondary_region="us-west-2",
            security_admin_account_id="111111111111",
            env=Environment(account="123456789012", region="us-east-1"),
        )
        factory = SiemSinksFactory(app, security_lake_stack)

        # When
        sink = factory.create_sink("splunk")

        # Then
        assert isinstance(sink, SplunkSink)

    def test_create_elastic_sink(self):
        """Test that factory creates Elastic sink."""
        # Given
        app = App()
        security_lake_stack = SecurityLakeStack(
            app,
            "test-security-lake",
            primary_region="us-east-1",
            secondary_region="us-west-2",
            security_admin_account_id="111111111111",
            env=Environment(account="123456789012", region="us-east-1"),
        )
        factory = SiemSinksFactory(app, security_lake_stack)

        # When
        sink = factory.create_sink("elastic")

        # Then
        assert isinstance(sink, ElasticSink)

    def test_create_invalid_sink(self):
        """Test that factory raises error for invalid sink type."""
        # Given
        app = App()
        security_lake_stack = SecurityLakeStack(
            app,
            "test-security-lake",
            primary_region="us-east-1",
            secondary_region="us-west-2",
            security_admin_account_id="111111111111",
            env=Environment(account="123456789012", region="us-east-1"),
        )
        factory = SiemSinksFactory(app, security_lake_stack)

        # When/Then
        with pytest.raises(ValueError, match="Unsupported SIEM sink type: invalid"):
            factory.create_sink("invalid")
