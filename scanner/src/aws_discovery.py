import boto3


def discover_ec2_instances() -> list[dict]:
    ec2 = boto3.client("ec2")
    response = ec2.describe_instances()

    instances = []
    for reservation in response["Reservations"]:
        for instance in reservation["Instances"]:
            instances.append(
                {
                    "resource_type": "ec2_instance",
                    "resource_id": instance["InstanceId"],
                    "instance_type": instance["InstanceType"],
                    "state": instance["State"]["Name"],
                    "region": instance["Placement"]["AvailabilityZone"][:-1],
                }
            )
    return instances

def discover_s3_buckets() -> list[dict]:
    s3 = boto3.client("s3")
    response = s3.list_buckets()

    return [
        {
            "resource_type": "s3_bucket",
            "resource_id": bucket["Name"],
            "created_at": bucket["CreationDate"].isoformat(),
        }
        for bucket in response["Buckets"]
    ]