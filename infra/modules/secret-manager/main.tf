variable "project" {}
variable "secret_names" { type = list(string) }
variable "accessor_sa_emails" { type = list(string) }

resource "google_secret_manager_secret" "secrets" {
  for_each  = toset(var.secret_names)
  secret_id = each.key

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_iam_member" "accessor" {
  for_each = {
    for pair in setproduct(var.secret_names, var.accessor_sa_emails) :
    "${pair[0]}:${pair[1]}" => { secret = pair[0], email = pair[1] }
  }

  secret_id = google_secret_manager_secret.secrets[each.value.secret].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${each.value.email}"
}
