*Cloud SQL Costs are prohibitive*

Cloud SQL for this small project would increase the bill about ~$25/month, because the database instance keeps running 24/7.

--> use neon.tech instead. neon is a postgresql database running on AWS which scales to 0. Drop in replacement.

Savings: ~$25/month → $0/month for the database tier.
