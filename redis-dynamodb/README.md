# Elastic Cached for Redis and DynamoDB 

[Reference - Deploy Amazon ElasticCache for Redis using AWS CDK](https://aws.amazon.com/blogs/database/deploy-amazon-elasticache-for-redis-using-aws-cdk/)


Customer stories  
- [Impatient web users 100ms means 1%$ sale loss](https://docs.aws.amazon.com/AmazonElastiCache/latest/mem-ug/elasticache-use-cases.html)
- [Tinder billions matches daily](https://aws.amazon.com/blogs/database/building-resiliency-at-scale-at-tinder-with-amazon-elasticache/?pg=ln&sec=c)
- [AppSync](https://docs.aws.amazon.com/appsync/latest/devguide/enabling-caching.html)
- [Game session](https://aws.amazon.com/blogs/gametech/building-a-presence-api-using-aws-appsync-aws-lambda-amazon-elasticache-and-amazon-eventbridge/)

When to use? 
- Speed and expense - expensive queries 
- Data and access pattern - relatively static and frequent accessed - personal profile

Performance
- [quotas](https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/quota-limits.html)
- [best best practice](https://d0.awsstatic.com/whitepapers/performance-at-scale-with-amazon-elasticache.pdf)
  - [Node type: M5 or R5](https://docs.aws.amazon.com/AmazonElastiCache/latest/mem-ug/nodes-select-size.html)
  - Launch in a private subnet 
  - Security group (Redis 6739, Memcached 11211)
  - Encryption TSL/SSL 
  - [Lazy vs write-through](https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/Strategies.html#Strategies.WriteThrough)

## Architecture 

<img width="842" alt="DBBLOG-1922-image001" src="https://user-images.githubusercontent.com/20411077/173473810-3c09d636-3445-4a6c-99c5-6c31db902079.png" />


## Redis Cluster Stack
```tsx
 // get existed vpc
    const vpc = aws_ec2.Vpc.fromLookup(this, "Vpc", {
      vpcId: props.vpcId,
      vpcName: props.vpcName,
    });

```
```tsx
 // subnet groups
    const subnetGroup = new aws_elasticache.CfnSubnetGroup(
      this,
      "SubnetGroupForRedisCluster",
      {
        subnetIds: vpc.privateSubnets.map((subnet) => subnet.subnetId),
        description: "subnet group for redis cluster",
      }
    );
```
```tsx
 // redis security group
    const redisSecurityGroup = new aws_ec2.SecurityGroup(
      this,
      "SecurityGroupForRedisCluster",
      {
        securityGroupName: "SecurityGroupForRedisCluster",
        vpc: vpc,
      }
    );

    redisSecurityGroup.addIngressRule(
      // production SG peer
      aws_ec2.Peer.securityGroupId(props.vscodeSecurityGroupId),
      // redis port
      aws_ec2.Port.tcp(6379)
    );

```

```tsx
// elasticache for redis cluster
    const redis = new aws_elasticache.CfnCacheCluster(
      this,
      "RedisClusterDmoe",
      {
        clusterName: "RedisClusterDemo",
        engine: "redis",
        cacheNodeType: "cache.t3.small",
        numCacheNodes: 1,
        cacheSubnetGroupName: subnetGroup.ref,
        vpcSecurityGroupIds: [redisSecurityGroup.securityGroupId],
      }
    );
```

## Redis Client Python 
environment variable 
```bash 
 export REDIS_HOSTNAME = 'REDIS_ENDPOINT'
```

```python
# redis endpoint 
HOST = os.environ["REDIS_HOSTNAME"].replace(":6379", "")
# boto3 db client
dynamodb = boto3.client("dynamodb")
# redis client
r = redis.Redis(host=HOST)
```
lazy loading
```python
def fetch_restaurant_summary(restaurant_name):
    """
    fetch from cache and write to cache 
    """
    # fetch from cache
    restaurant = fetch_restaurant_summary_from_cache(restaurant_name)
    # hit cache and return 
    if restaurant:
        return restaurant
    # mis-cache and fetch from db
    restaurant = fetch_restaurant_summary_from_local(restaurant_name)
    # write to cache 
    store_restaurant_summary_in_cache(restaurant)
    # print response 
    print("Using uncached result!")
    return restaurant
```

## DynamoDB Table 
create a restaurant table with global secondary index 
```python
import boto3

dynamodb = boto3.client("dynamodb")

try:
    dynamodb.create_table(
        TableName="Restaurants",
        AttributeDefinitions=[
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "SK", "AttributeType": "S"},
            {"AttributeName": "GSI1PK", "AttributeType": "S"},
            {"AttributeName": "GSI1SK", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "GSI1",
                "KeySchema": [
                    {"AttributeName": "GSI1PK", "KeyType": "HASH"},
                    {"AttributeName": "GSI1SK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 5,
                    "WriteCapacityUnits": 5,
                },
            }
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    print("Table created successfully.")
except Exception as e:
    print("Could not create table. Error:")
    print(e)
```

bach writing the table 
```python
import json
import boto3

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("Restaurants")
items = []

with open("scripts/items.json", "r") as f:
    for row in f:
        items.append(json.loads(row))

with table.batch_writer() as batch:
    for item in items:
        batch.put_item(Item=item)

print("Items loaded successfully.")

```

## Caching Performance 
```python
  names = scan_restaurant(limit=100)
  db_latencies = [fetch_restaurant_summary_from_db(name).latency for name in names]
  cache_latencies = [fetch_restaurant_summary(name).latency for name in names]
  plot_performance(db_latencies[1:], cache_latencies[1:])
```