# DynamoDB DAX Performance 
[Customers: Tinder, Cannon, Careem](https://aws.amazon.com/dynamodb/dax/)


[What use cases/When to use?](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DAX.html) 
- Single digit milisecond latency
- Less operation and complexity 
- Handle read-heavy and bursty workloads 

Concepts/Parameters:
- [Consistency model](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DAX.consistency.html)
- [Modify application](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DAX.client.modify-your-app.html)
- [TTL setting](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DAX.cluster-management.html#DAX.cluster-management.custom-settings.ttl)
- [Encryption, KMS, TLS](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DAXEncryptionInTransit.html)

References:
- [Read/Write-through cache - transparent to application](https://aws.amazon.com/blogs/database/amazon-dynamodb-accelerator-dax-a-read-throughwrite-through-cache-for-dynamodb/)


## Architecture 
![dax_high_level e4af7cc27485497eff5699cdf22a9502496cba38](https://user-images.githubusercontent.com/20411077/173214194-f539fe34-638a-4ad0-b1e7-16dc7dfef642.png)
![dax_performance](https://user-images.githubusercontent.com/20411077/173296706-6ad579f8-9a89-4bc7-bd37-313b6cacfa49.png)


## DAX Cluster Stack 
subnet group 
```tsx
// get existed vpc
    const vpc = aws_ec2.Vpc.fromLookup(this, "Vpc", {
      vpcId: props.vpcId,
      vpcName: props.vpcName,
    });

// subnet groups
const subnetGroup = new aws_dax.CfnSubnetGroup(
  this,
  "SubnetGroupForDaxDemo",
  {
    description: "subnet group for dax demo",
    subnetGroupName: "SubnetGroupForDaxDemo",
    // nice map
    subnetIds: vpc.privateSubnets.map(
      (subnet) => subnet.subnetId
    ),
  }
); 
```
parameter group 
```tsx
const parameterGroup = new aws_dax.CfnParameterGroup(
      this,
      "ParameterGroupDaxDemo",
      {
        parameterGroupName: "ParameterGroupDaxDemo",
        description: "parameter gropu for dax cluster demo",
        // default 5 minutes 300000 milisesconds
        parameterNameValues: {
          "query-ttl-millis": "300000",
          "record-ttl-millis": "180000",
        },
      }
    );
```
role for DAX 
```tsx
// role for dax cluster
    const role = new aws_iam.Role(
      this,
      "RoleForDaxClusterDmoe",
      {
        roleName: "RoleForDaxClusterDemo",
        assumedBy: new aws_iam.ServicePrincipal(
          "dax.amazonaws.com"
        ),
      }
    );

    role.attachInlinePolicy(
      new aws_iam.Policy(this, "PolicyForDaxClusterDmoe", {
        policyName: "PolicyForDaxClusterDmoe",
        statements: [
          new aws_iam.PolicyStatement({
            effect: aws_iam.Effect.ALLOW,
            actions: ["dynamodb:*"],
            resources: ["*"],
          }),
        ],
      })
    );
```
security group for DAX cluster 
```tsx
// security group 
    const securityGroup = new aws_ec2.SecurityGroup(
      this,
      "SecurityGroupForDaxCluster",
      {
        securityGroupName: "SecurityGroupForDaxCluster",
        vpc: vpc
      }
    )

    securityGroup.addIngressRule(
      // production SG peer 
      aws_ec2.Peer.anyIpv4(),
      // unencrypted 8111
      aws_ec2.Port.tcp(8111),
    )
```
create a DAX cluster 
```tsx
 // create a dax cluster
  new aws_dax.CfnCluster(this, "DaxClusterDemo", {
    clusterName: "DaxClusterDemo",
    // role to access ddb
    iamRoleArn: role.roleArn,
    // mem optimized node type
    nodeType: "dax.r4.large",
    // 3: 1 primary and 2 read replics
    replicationFactor: 3,
    // automatically into az
    // availabilityZones: [''],
    // encryption TSL or NONE as default
    clusterEndpointEncryptionType: "NONE",
    // notificationTopicArn: "",
    parameterGroupName: parameterGroup.parameterGroupName,
    // range of time maintenance of DAX software performed
    // preferredMaintenanceWindow: "",
    securityGroupIds: [
      securityGroup.securityGroupId
    ],
    subnetGroupName: subnetGroup.subnetGroupName,
  });
```

## DAX Performance Check 
[amazondax python client](https://pypi.org/project/amazon-dax-client/) 
```python 
  # dax client 
  dax = amazondax.AmazonDaxClient.resource(
    endpoint_url=DAX_ENDPOINT
  )
```
```python 
def get_items_wi_dax(table_name: str, no_iter: int) -> Double:
  """
  measure time when getting items with dax 
  """
  # dax client 
  dax = amazondax.AmazonDaxClient.resource(
    endpoint_url=DAX_ENDPOINT
  )
  # table  
  table = dax.Table(table_name)
  # start time 
  start = time.time()
  # loop no_iter
  for k in range(no_iter):
    # loop over user_ids
    for user_id in USER_IDS:
      # query by user_id 
      res = table.query(
        KeyConditionExpression=Key('UserId').eq(user_id),
        ScanIndexForward=False)
      # print(res)
  # end time 
  end = time.time()
  # time lag
  time_lag = (end - start) * 1000 
  print(f'with dax: time lag total: {time_lag}ms, per loop: {time_lag/no_iter}ms, per query: {time_lag/(no_iter * len(USER_IDS))}ms')
  # return 
  return time_lag/(no_iter * len(USER_IDS))
```

## DynamoDB Table and Prepare Data 
```python
def create_table(table_name: str) -> None:
    """
    create a table
    """
    # db client, optional region specified here
    db_client = boto3.client('dynamodb')
    # create a table
    res = db_client.create_table(
        TableName=table_name,
        AttributeDefinitions=[
            {
                'AttributeName': 'UserId',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'CreatedTime',
                'AttributeType': 'N'
            },
        ],
        # KeySchema and Attribute should be the same
        KeySchema=[
            {
                'AttributeName': 'UserId',
                'KeyType': 'HASH'
            },
            {
                'AttributeName': 'CreatedTime',
                'KeyType': 'RANGE'
            },
        ],
        # PAY_PER_REQUEST when load is unpredictable
        # PROVISIONED when load is predictable
        BillingMode="PAY_PER_REQUEST"
    )
    # print table meta data 
    print(res)
```
write data to a table
```python
def write_table(table_name: str) -> None:
  """
  write data items to a table 
  """
  # table 
  table = get_table(table_name)
  # create a new item
  for game_title in GAME_TITLES:
      for user_id in USER_IDS:
          res = table.put_item(
              Item={
                  'UserId': user_id,
                  'GameTitle': game_title,
                  'Score': random.randint(1000, 6000),
                  'Wins': random.randint(0, 100),
                  'Losses': random.randint(5, 50),
                  'CreatedTime': int(datetime.datetime.now().timestamp() * 1000)
              }
          )
          print(res)
```

## Get item with DAX client 
```python 
def get_items_by_primary_key(table: str, mode='dax', no_iter=10):
  """
  """
  # buffer time lags 
  time_lags = []
  # table 
  if mode=='dax':
    # dax client 
    dax = amazondax.AmazonDaxClient.resource(
      endpoint_url=DAX_ENDPOINT
    )
    # table  
    table = dax.Table(table_name)
  else:
    table = get_table(table_name)
  # loop get item 
  for k in range(no_iter):
    start = time.perf_counter()
    res = table.get_item(
      Key={"UserId": "120", "CreatedTime": 1655098896759}
    )
    end = time.perf_counter()
    # time lag in ms 
    duration = (end - start) * 1000
    print(f'{mode} et-item latency: {duration:.4f}ms')
    time_lags.append(duration)
    # response 
    print(res)
  # return 
  return time_lags
```