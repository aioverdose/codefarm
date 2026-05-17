module "demo_staging_web_20260516170834" {
  source = "./modules/nginx-vm"
  name   = "demo-staging-web-20260516170834"
  memory = 2048
  cpu    = 2
  disk   = 20
}
