# nginx-vm module placeholder for the commercial CodeFarm demo.
variable "name" { type = string }
variable "memory" { type = number }
variable "cpu" { type = number }
variable "disk" { type = number }

output "service_name" { value = var.name }
