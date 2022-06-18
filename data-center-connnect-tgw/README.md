# Transit Gateway with A Simulated On-Premises Data Center 

## Architecture 

## Simulated On-Premise 

## AWS Base Network Stack 
vpc for development department 
```tsx
 // vpc-ec2 for dev development
    this.developmentVpc = new VpcWithEc2(this, "Development", {
      prefix: "Development",
      cidr: cfnParams[this.region].DevelopmentCidr,
      cidrMask: cfnParams[this.region].CidrMask,
      ec2Role: this.ec2Role,
    });
```
vpc for production department 
```tsx
 // vpc-ec2 prod department
    this.productionVpc = new VpcWithEc2(this, "Production", {
      prefix: "Production",
      cidr: cfnParams[this.region].ProductionCidr,
      cidrMask: cfnParams[this.region].CidrMask,
      ec2Role: this.ec2Role,
    });
```

## Option. Simulated On-Prem 
```tsx
export class SimulatedOnPremFromWorkShop extends Stack {
  constructor(scope: Construct, id: string, props: StackProps) {
    super(scope, id, props);

    new cloudformation_include.CfnInclude(this, "SimulatedOnPrem", {
      templateFile: "./lib/simulated-on-prem.yaml",
    });
  }
}
```

## Transit Gateway, Customer Gateway, VPN Connection 
create a TGW 
```tsx 
// create an TGW
    this.cfnTransitGateway = new aws_ec2.CfnTransitGateway(
      this,
      props.prefix!.concat("-TGW").toString(),
      {
        amazonSideAsn: props.amazonSideAsn,
        description: "TGW for hybrid networking",
        autoAcceptSharedAttachments: "enable",
        defaultRouteTableAssociation: "enable",
        defaultRouteTablePropagation: "enable",
        dnsSupport: "enable",
        vpnEcmpSupport: "enable",
        multicastSupport: "enable",
        tags: [
          {
            key: "Name",
            value: props.prefix!.concat("-TGW").toString(),
          },
        ],
      }
    );
```
create a customer gateway 
```tsx
// create a customer gateway
    this.cfnCustomerGateway = new aws_ec2.CfnCustomerGateway(
      this,
      props.prefix!.concat("-CGW").toString(),
      {
        bgpAsn: props.customerSideAsn!,
        ipAddress: props.onPremIpAddress!,
        type: "ipsec.1",
        tags: [
          {
            key: "Name",
            value: props.prefix!.concat("-CGW").toString(),
          },
        ],
      }
    );
```
create a vpn connection 
```tsx
// create the site-to-site VPN connection
    this.cfnVPNConnection = new aws_ec2.CfnVPNConnection(
      this,
      props.prefix!.concat("-VPN").toString(),
      {
        transitGatewayId: this.cfnTransitGateway.ref,
        customerGatewayId: this.cfnCustomerGateway.ref,
        staticRoutesOnly: false,
        type: "ipsec.1",
        tags: [
          {
            key: "Name",
            value: props.prefix!.concat("-VPN").toString(),
          },
        ],
      }
    );
```

## Transit Gateway Routes, Attachments 
create a tgw route table
```tsx
// tgw route table
    this.cfnTransitGatewayRouteTable = new aws_ec2.CfnTransitGatewayRouteTable(
      this,
      props.prefix!.concat("-RouteTable").toString(),
      {
        transitGatewayId: props.transitGateway.ref,
        tags: [
          {
            key: "Name",
            value: props.prefix!.concat("-RouteTable").toString(),
          },
        ],
      }
    );
```
create development tgw-development-vpc-attachment
```tsx
// create development tgw-development-vpc-attachment
    const tgwDevVpcAttachment = new aws_ec2.CfnTransitGatewayAttachment(
      this,
      props.prefix!.concat("dev-vpc-tgw-attachment").toString(),
      {
        transitGatewayId: props.transitGateway.ref,
        vpcId: props.developmentVpc.vpcId,
        subnetIds: props.developmentVpc.isolatedSubnets.map(
          (subnet) => subnet.subnetId
        ),
        tags: [
          {
            key: "Name",
            value: props.prefix!.concat("dev-vpc-tgw-attachment").toString(),
          },
        ],
      }
    );
```
create development tgw-production-vpc-attachment
```tsx
// create development tgw-production-vpc-attachment
    const tgwProdVpcAttachment = new aws_ec2.CfnTransitGatewayAttachment(
      this,
      props.prefix!.concat("prod-vpc-tgw-attachment").toString(),
      {
        transitGatewayId: props.transitGateway.ref,
        vpcId: props.productionVpc.vpcId,
        subnetIds: props.productionVpc.isolatedSubnets.map(
          (subnet) => subnet.subnetId
        ),
        tags: [
          {
            key: "Name",
            value: props.prefix!.concat("prod-vpc-tgw-attachment").toString(),
          },
        ],
      }
    );
```
development-vpc-attachment and tgw-table association
```tsx
const tgwDevVpcAttRoutTableAssociation =
      new aws_ec2.CfnTransitGatewayRouteTableAssociation(
        this,
        "dev-vpc-attachment-tgw-route-table-association",
        {
          transitGatewayRouteTableId: this.cfnTransitGatewayRouteTable.ref,
          transitGatewayAttachmentId: tgwDevVpcAttachment.ref,
        }
      );
```
production-vpc-attachment and tgw-table association
```tsx
const tgwProdVpcAttRoutTableAssociation =
      new aws_ec2.CfnTransitGatewayRouteTableAssociation(
        this,
        "prod-vpc-attachment-tgw-route-table-association",
        {
          transitGatewayRouteTableId: this.cfnTransitGatewayRouteTable.ref,
          transitGatewayAttachmentId: tgwProdVpcAttachment.ref,
        }
      );
```

dev-vpc-attachment tgw-propogation
```tsx
// dev-vpc-attachment tgw-propogation
    new aws_ec2.CfnTransitGatewayRouteTablePropagation(
      this,
      "dev-vpc-attachment-tgw-route-table-propogation",
      {
        transitGatewayRouteTableId: this.cfnTransitGatewayRouteTable.ref,
        transitGatewayAttachmentId: tgwDevVpcAttachment.ref,
      }
    );
```
prod-vpc-attachment tgw-propogation
```tsx
 // prod-vpc-attachment tgw-propogation
    new aws_ec2.CfnTransitGatewayRouteTablePropagation(
      this,
      "prod-vpc-attachment-tgw-route-table-propogation",
      {
        transitGatewayRouteTableId: this.cfnTransitGatewayRouteTable.ref,
        transitGatewayAttachmentId: tgwProdVpcAttachment.ref,
      }
    );
```

### VPC Subnet Routes Update 
development vpc subnets route update
```tsx
// development vpc subnets route update
    for (var subnet of props.developmentVpc.isolatedSubnets) {
      var route = new aws_ec2.CfnRoute(this, "RouteToProdVpcDepartment", {
        routeTableId: subnet.routeTable.routeTableId,
        // vpc cidr here
        destinationCidrBlock: props.productionVpc.vpcCidrBlock,
        transitGatewayId: props.transitGateway.ref,
      });
      // route.addDependsOn(vpcDevTgwAttach);
      route.addDependsOn(tgwDevVpcAttachment);
    }
```
production vpc subnets route update
```tsx
// production vpc subnets route update
    for (var subnet of props.productionVpc.isolatedSubnets) {
      var route = new aws_ec2.CfnRoute(this, "RouteToDevVpcDepartment", {
        routeTableId: subnet.routeTable.routeTableId,
        // vpc cidr here
        destinationCidrBlock: props.developmentVpc.vpcCidrBlock,
        transitGatewayId: props.transitGateway.ref,
      });
      // route.addDependsOn(vpcDevTgwAttach);
      route.addDependsOn(tgwDevVpcAttachment);
    }
```

## Vpc with Ec2 Stack 
vpc for dev department 
```tsx
// vpc with isolated subnet
    this.vpc = new aws_ec2.Vpc(this, props.prefix!.concat("-VPC").toString(), {
      vpcName: props.prefix!.concat("-VPC"),
      cidr: props.cidr,
      maxAzs: 1,
      subnetConfiguration: [
        {
          cidrMask: props.cidrMask,
          name: props.prefix!.concat("-VPC | ISOLATED"),
          subnetType: aws_ec2.SubnetType.PRIVATE_ISOLATED,
        },
      ],
    });
```
security group for ec2 allow ICMP-ping
```tsx
// security group for ec2
this.securityGroup = new aws_ec2.SecurityGroup(
  this,
  props.prefix!.concat("-SG").toString(),
  {
    vpc: this.vpc,
    description: "Allow ICMP ping and HTTPS",
  }
);

// allow inbound ICMP ping
this.securityGroup.addIngressRule(
  aws_ec2.Peer.anyIpv4(),
  aws_ec2.Port.allIcmp(),
  "Allow ICMP"
);
```
add ssm (3 endpoints needed isolated subnet)
```tsx
// vpc endpoints ssm (3 needed)
new aws_ec2.InterfaceVpcEndpoint(
  this,
  props.prefix!.concat("-SSM").toString(),
  {
    service: aws_ec2.InterfaceVpcEndpointAwsService.SSM,
    vpc: this.vpc,
    privateDnsEnabled: true,
    subnets: this.vpc.selectSubnets({
      subnetType: aws_ec2.SubnetType.PRIVATE_ISOLATED,
    }),
  }
);

new aws_ec2.InterfaceVpcEndpoint(
  this,
  props.prefix!.concat("-SSM-MESSAGES").toString(),
  {
    service: aws_ec2.InterfaceVpcEndpointAwsService.SSM_MESSAGES,
    vpc: this.vpc,
    privateDnsEnabled: true,
    subnets: this.vpc.selectSubnets({
      subnetType: aws_ec2.SubnetType.PRIVATE_ISOLATED,
    }),
  }
);

new aws_ec2.InterfaceVpcEndpoint(
  this,
  props.prefix!.concat("-EC2-MESSAGES").toString(),
  {
    service: aws_ec2.InterfaceVpcEndpointAwsService.EC2_MESSAGES,
    vpc: this.vpc,
    privateDnsEnabled: true,
    subnets: this.vpc.selectSubnets({
      subnetType: aws_ec2.SubnetType.PRIVATE_ISOLATED,
    }),
  }
);
```

role for ec2 
```tsx
// ec2 role
    this.ec2Role = new aws_iam.Role(this, "svcRoleForEc2ViaSsm", {
      assumedBy: new aws_iam.ServicePrincipal("ec2.amazonaws.com"),
      description: "Service role for EC2 access via SSM session manager",
      managedPolicies: [
        aws_iam.ManagedPolicy.fromAwsManagedPolicyName(
          "AmazonSSMManagedInstanceCore"
        ),
        aws_iam.ManagedPolicy.fromAwsManagedPolicyName(
          "AmazonSSMPatchAssociation"
        ),
      ],
    });
```

create an ec2
```tsx
const ec2 = new aws_ec2.Instance(
  this,
  props.prefix!.concat("-Instance").toString(),
  {
    instanceType: aws_ec2.InstanceType.of(
      aws_ec2.InstanceClass.T2,
      aws_ec2.InstanceSize.MICRO
    ),
    role: props.ec2Role,
    securityGroup: this.securityGroup,
    vpc: this.vpc,
    machineImage: new aws_ec2.AmazonLinuxImage({
      cpuType: aws_ec2.AmazonLinuxCpuType.X86_64,
      generation: aws_ec2.AmazonLinuxGeneration.AMAZON_LINUX_2,
    }),
  }
);
ec2.node.addDependency(this.vpc);
```
