variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "zone" {
  type = string
}

variable "cluster_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "name_prefix" {
  type = string
}

variable "network_self_link" {
  type = string
}

variable "subnetwork_self_link" {
  type = string
}

variable "pods_range_name" {
  type = string
}

variable "services_range_name" {
  type = string
}

variable "authorized_networks" {
  type = list(object({
    cidr_block   = string
    display_name = string
  }))
}

variable "initial_node_count" {
  type = number
}

variable "min_node_count" {
  type = number
}

variable "max_node_count" {
  type = number
}

variable "node_machine_type" {
  type = string
}
