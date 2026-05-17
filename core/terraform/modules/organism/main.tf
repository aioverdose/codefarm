variable "name" { type = string }
variable "memory" { type = number }
variable "cpu" { type = number }

output "organism_name" {
  value = var.name
}
