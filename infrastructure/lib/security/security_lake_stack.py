from aws_cdk import Stack
from constructs import Construct


class SecurityLakeStack(Stack):
    """
    This stack configures AWS Security Lake.
    It defines the data lake and configures log sources from the organization.
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Resources for Security Lake will be defined here.
