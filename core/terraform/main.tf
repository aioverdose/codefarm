terraform {
  required_version = ">= 1.6.0"
}

variable "codefarm_root" {
  type    = string
  default = "G:/codefarm"
}

# Added by org-001 at 2026-05-16T17:13:58.328824+00:00
module "organism_7554" {
  source = "./modules/organism"
  name   = "auto-org-5064"
  memory = 2048
  cpu    = 2
}

# Added by org-003 at 2026-05-16T17:13:58.482628+00:00
module "organism_2585" {
  source = "./modules/organism"
  name   = "auto-org-8893"
  memory = 2048
  cpu    = 2
}

# Added by org-001 at 2026-05-16T17:30:11.794324+00:00
module "organism_6096" {
  source = "./modules/organism"
  name   = "auto-org-5801"
  memory = 2048
  cpu    = 2
}

# Added by org-001 at 2026-05-16T17:36:16.965126+00:00
module "organism_8492" {
  source = "./modules/organism"
  name   = "auto-org-9263"
  memory = 2048
  cpu    = 2
}

# Added by org-001 at 2026-05-16T18:28:08.209798+00:00
module "organism_5496" {
  source = "./modules/organism"
  name   = "auto-org-2099"
  memory = 2048
  cpu    = 2
}

# Added by org-001 at 2026-05-16T18:38:03.416034+00:00
module "organism_3241" {
  source = "./modules/organism"
  name   = "auto-org-8926"
  memory = 2048
  cpu    = 2
}

# Added by org-001 at 2026-05-16T18:38:41.822004+00:00
module "organism_4393" {
  source = "./modules/organism"
  name   = "auto-org-8908"
  memory = 2048
  cpu    = 2
}

# Added by org-001 at 2026-05-16T21:19:16.429532+00:00
module "organism_6312" {
  source = "./modules/organism"
  name   = "auto-org-3439"
  memory = 2048
  cpu    = 2
}

# Proposed by org-002 at 2026-05-17T00:27:14.519545+00:00
module "organism_6097" {
  source = "./modules/organism"
  name   = "auto-org-1881"
  memory = 2048
  cpu    = 2
}

# Proposed by org-004 at 2026-05-17T00:27:16.067618+00:00
module "organism_3856" {
  source = "./modules/organism"
  name   = "auto-org-4238"
  memory = 2048
  cpu    = 2
}

# Proposed by org-005 at 2026-05-17T00:27:16.734517+00:00
module "organism_2981" {
  source = "./modules/organism"
  name   = "auto-org-2001"
  memory = 2048
  cpu    = 2
}

# Proposed by org-006 at 2026-05-17T00:27:17.467800+00:00
module "organism_8323" {
  source = "./modules/organism"
  name   = "auto-org-1721"
  memory = 2048
  cpu    = 2
}
