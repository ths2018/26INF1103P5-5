import data_manager

mgr = data_manager.get_manager()
print(type(mgr.repository).__name__)   # should print MongoCaseRepository
print([c.case_id for c in mgr.list_cases()])