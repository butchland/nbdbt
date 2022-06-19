# TODO

* Patch FalDbt to allow it to get analyses models 
* Add retrieval of FalDBT object to dbt cell magic so that you can optionally run a preview of the sql using faldbt objects (with optional limit clause)
* Add caching of update time for write_sql so that if update_time matches file time
for existing models, it won't rewrite it each time or execute the compilation
* Add script to setup my_dbt_project dir for testing

