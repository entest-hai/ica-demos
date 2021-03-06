import { aws_ec2, CfnOutput, Fn, Stack, StackProps } from "aws-cdk-lib";
import { Construct } from "constructs";

export interface SimulatedOnPremProps extends StackProps {
  readonly prefix?: string;
  readonly cidr?: string;
  readonly cidrMask?: number;
}

export class SimulatedOnPrem extends Stack {
  public readonly eip: aws_ec2.CfnEIP;
  public readonly vpc: aws_ec2.Vpc;

  constructor(scope: Construct, id: string, props: SimulatedOnPremProps) {
    super(scope, id, props);

    // elastic ip
    this.eip = new aws_ec2.CfnEIP(this, "onPremEip");
    const allocationId = Fn.getAtt(this.eip.logicalId, "AllocationId");

    // create a vpc with public subnet
    this.vpc = new aws_ec2.Vpc(this, props.prefix!.concat("-VPC").toString(), {
      vpcName: props.prefix!.concat("-VPC"),
      cidr: props.cidr,
      maxAzs: 1,
      subnetConfiguration: [
        {
          cidrMask: props.cidrMask,
          name: props.prefix!.concat("-VPC | Public"),
          subnetType: aws_ec2.SubnetType.PUBLIC,
        },
      ],
    });

    // security group for ec2
    const sg = new aws_ec2.SecurityGroup(this, "SecurityGroupForEc2OpenSwan", {
      securityGroupName: "SecurityGroupForEc2OpenSwan",
      vpc: this.vpc,
    });

    sg.addIngressRule(aws_ec2.Peer.anyIpv4(), aws_ec2.Port.tcp(22));
    sg.addIngressRule(aws_ec2.Peer.anyIpv4(), aws_ec2.Port.allIcmp());

    // ec2 openswan as customer router
    const ec2 = new aws_ec2.Instance(this, "OnPremEc2", {
      instanceName: "OnPremEc2",
      instanceType: aws_ec2.InstanceType.of(
        aws_ec2.InstanceClass.T2,
        aws_ec2.InstanceSize.SMALL
      ),
      machineImage: new aws_ec2.AmazonLinuxImage({
        cpuType: aws_ec2.AmazonLinuxCpuType.X86_64,
        generation: aws_ec2.AmazonLinuxGeneration.AMAZON_LINUX_2,
      }),
      vpc: this.vpc,
      vpcSubnets: {
        subnetType: aws_ec2.SubnetType.PUBLIC,
      },
      securityGroup: sg,
    });

    // output
    new CfnOutput(this, "eipAllocationId", {
      description: "EIP allocation ID",
      exportName: "eipAllocationId",
      value: allocationId.toString(),
    });
  }
}
