# Pick two AZs dynamically rather than hardcoding — portable across regions.
data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_vpc" "main" {
  # checkov:skip=CKV2_AWS_11:VPC flow logs intentionally off — they bill CloudWatch ingestion for little benefit in this sandbox; the ALB chokepoint + task SG provide access control. Revisit for a real environment.
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true # so the ALB + task ENIs get resolvable DNS names

  tags = { Name = "ccg-backend" }
}

# The door to the internet. Without it (and the route below), the subnets are private.
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "ccg-backend" }
}

# Two PUBLIC subnets across two AZs — an ALB requires >= 2 AZs. cidrsubnet()
# carves /24s out of the VPC /16: 10.0.0.0/24 (index 0), 10.0.1.0/24 (index 1).
resource "aws_subnet" "public" {
  # checkov:skip=CKV_AWS_130:Public subnets by design — the no-NAT architecture puts Fargate tasks in public subnets with public IPs so they can reach AWS APIs; they're protected by the task SG (admits only the ALB), not by being private. Saves ~$32/mo of NAT.
  count                   = 2
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, count.index)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = { Name = "ccg-backend-public-${count.index}" }
}

# A subnet is "public" ONLY because its route table sends 0.0.0.0/0 to the IGW.
# Public/private is routing, not a flag.
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = { Name = "ccg-backend-public" }
}

resource "aws_route_table_association" "public" {
  count          = 2
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}
