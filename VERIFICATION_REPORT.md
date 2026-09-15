# Verification report v10

## Python compilation
Compiled: 27
Errors: 0
PASS

## Static release audit
Exit: 0
```
RELEASE AUDIT
WARN: docker-compose.yml contains development defaults; never use them in production
RESULT: PASS
Spreadsheet runtime warmup failed during python startup
Traceback (most recent call last):
  File "/tmp/tmp.L2TH2Y5coc/artifact_tool_v2-2.8.22/artifact_tool/patches/warm_spreadsheet_runtime_on_startup.py", line 26, in warm_spreadsheet_runtime_on_startup
  File "/tmp/tmp.L2TH2Y5coc/artifact_tool_v2-2.8.22/artifact_tool/spreadsheet_warmup.py", line 785, in warm_spreadsheet_runtime
  File "/tmp/tmp.L2TH2Y5coc/artifact_tool_v2-2.8.22/artifact_tool/spreadsheet_warmup.py", line 720, in _warm_feature_flows
  File "/tmp/tmp.L2TH2Y5coc/artifact_tool_v2-2.8.22/artifact_tool/spreadsheet_warmup.py", line 704, in _warm_collaboration_flows
  File "/tmp/tmp.L2TH2Y5coc/artifact_tool_v2-2.8.22/artifact_tool/generated/interface/models.py", line 32317, in hydrate_crdt_from_proto
  File "/tmp/tmp.L2TH2Y5coc/artifact_tool_v2-2.8.22/artifact_tool/rpc/remote.py", line 749, in __call__
  File "/tmp/tmp.L2TH2Y5coc/artifact_tool_v2-2.8.22/artifact_tool/rpc/client.py", line 150, in call
artifact_tool.rpc.client.RemoteError: hydrateCrdtFromProto requires an empty collaborative document.
```

## Pytest
Exit: 2
```
_____________[0m
[31mImportError while importing test module '/mnt/data/private_club_v10/tests/test_e2e_core.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
[1m[31m/usr/lib/python3.13/importlib/__init__.py[0m:88: in import_module
    [0m[94mreturn[39;49;00m _bootstrap._gcd_import(name[level:], package, level)[90m[39;49;00m
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^[90m[39;49;00m
[1m[31mtests/test_e2e_core.py[0m:5: in <module>
    [0m[94mfrom[39;49;00m[90m [39;49;00m[04m[96mapp[39;49;00m[04m[96m.[39;49;00m[04m[96mmain[39;49;00m[90m [39;49;00m[94mimport[39;49;00m app[90m[39;49;00m
[1m[31mapp/main.py[0m:286: in <module>
    [0m[94mfrom[39;49;00m[90m [39;49;00m[04m[96m.[39;49;00m[04m[96mauth_v6[39;49;00m[90m [39;49;00m[94mimport[39;49;00m issue [94mas[39;49;00m v6_issue,current [94mas[39;49;00m v6_current,rate [94mas[39;49;00m v6_rate[90m[39;49;00m
[1m[31mapp/auth_v6.py[0m:3: in <module>
    [0m[94mfrom[39;49;00m[90m [39;49;00m[04m[96m.[39;49;00m[04m[96mredis_store[39;49;00m[90m [39;49;00m[94mimport[39;49;00m create_session,resolve_session,revoke_session,limited[90m[39;49;00m
[1m[31mapp/redis_store.py[0m:2: in <module>
    [0m[94mfrom[39;49;00m[90m [39;49;00m[04m[96mredis[39;49;00m[90m [39;49;00m[94mimport[39;49;00m Redis[90m[39;49;00m
[1m[31mE   ModuleNotFoundError: No module named 'redis'[0m[0m
[31m[1m_______________ ERROR collecting tests/test_security_headers.py ________________[0m
[31mImportError while importing test module '/mnt/data/private_club_v10/tests/test_security_headers.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
[1m[31m/usr/lib/python3.13/importlib/__init__.py[0m:88: in import_module
    [0m[94mreturn[39;49;00m _bootstrap._gcd_import(name[level:], package, level)[90m[39;49;00m
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^[90m[39;49;00m
[1m[31mtests/test_security_headers.py[0m:5: in <module>
    [0m[94mfrom[39;49;00m[90m [39;49;00m[04m[96mapp[39;49;00m[04m[96m.[39;49;00m[04m[96mmain[39;49;00m[90m [39;49;00m[94mimport[39;49;00m app[90m[39;49;00m
[1m[31mapp/main.py[0m:286: in <module>
    [0m[94mfrom[39;49;00m[90m [39;49;00m[04m[96m.[39;49;00m[04m[96mauth_v6[39;49;00m[90m [39;49;00m[94mimport[39;49;00m issue [94mas[39;49;00m v6_issue,current [94mas[39;49;00m v6_current,rate [94mas[39;49;00m v6_rate[90m[39;49;00m
[1m[31mapp/auth_v6.py[0m:3: in <module>
    [0m[94mfrom[39;49;00m[90m [39;49;00m[04m[96m.[39;49;00m[04m[96mredis_store[39;49;00m[90m [39;49;00m[94mimport[39;49;00m create_session,resolve_session,revoke_session,limited[90m[39;49;00m
[1m[31mapp/redis_store.py[0m:2: in <module>
    [0m[94mfrom[39;49;00m[90m [39;49;00m[04m[96mredis[39;49;00m[90m [39;49;00m[94mimport[39;49;00m Redis[90m[39;49;00m
[1m[31mE   ModuleNotFoundError: No module named 'redis'[0m[0m
[31m[1m_____________________ ERROR collecting tests/test_smoke.py _____________________[0m
[31mImportError while importing test module '/mnt/data/private_club_v10/tests/test_smoke.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
[1m[31m/usr/lib/python3.13/importlib/__init__.py[0m:88: in import_module
    [0m[94mreturn[39;49;00m _bootstrap._gcd_import(name[level:], package, level)[90m[39;49;00m
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^[90m[39;49;00m
[1m[31mtests/test_smoke.py[0m:5: in <module>
    [0m[94mfrom[39;49;00m[90m [39;49;00m[04m[96mapp[39;49;00m[04m[96m.[39;49;00m[04m[96mmain[39;49;00m[90m [39;49;00m[94mimport[39;49;00m app[90m[39;49;00m
[1m[31mapp/main.py[0m:286: in <module>
    [0m[94mfrom[39;49;00m[90m [39;49;00m[04m[96m.[39;49;00m[04m[96mauth_v6[39;49;00m[90m [39;49;00m[94mimport[39;49;00m issue [94mas[39;49;00m v6_issue,current [94mas[39;49;00m v6_current,rate [94mas[39;49;00m v6_rate[90m[39;49;00m
[1m[31mapp/auth_v6.py[0m:3: in <module>
    [0m[94mfrom[39;49;00m[90m [39;49;00m[04m[96m.[39;49;00m[04m[96mredis_store[39;49;00m[90m [39;49;00m[94mimport[39;49;00m create_session,resolve_session,revoke_session,limited[90m[39;49;00m
[1m[31mapp/redis_store.py[0m:2: in <module>
    [0m[94mfrom[39;49;00m[90m [39;49;00m[04m[96mredis[39;49;00m[90m [39;49;00m[94mimport[39;49;00m Redis[90m[39;49;00m
[1m[31mE   ModuleNotFoundError: No module named 'redis'[0m[0m
[36m[1m=========================== short test summary info ============================[0m
[31mERROR[0m tests/test_e2e_core.py
[31mERROR[0m tests/test_security_headers.py
[31mERROR[0m tests/test_smoke.py
!!!!!!!!!!!!!!!!!!! Interrupted: 3 errors during collection !!!!!!!!!!!!!!!!!!!!
[31m[31m[1m3 errors[0m[31m in 0.84s[0m[0m
Spreadsheet runtime warmup failed during python startup
Traceback (most recent call last):
  File "/tmp/tmp.L2TH2Y5coc/artifact_tool_v2-2.8.22/artifact_tool/patches/warm_spreadsheet_runtime_on_startup.py", line 26, in warm_spreadsheet_runtime_on_startup
  File "/tmp/tmp.L2TH2Y5coc/artifact_tool_v2-2.8.22/artifact_tool/spreadsheet_warmup.py", line 785, in warm_spreadsheet_runtime
  File "/tmp/tmp.L2TH2Y5coc/artifact_tool_v2-2.8.22/artifact_tool/spreadsheet_warmup.py", line 720, in _warm_feature_flows
  File "/tmp/tmp.L2TH2Y5coc/artifact_tool_v2-2.8.22/artifact_tool/spreadsheet_warmup.py", line 704, in _warm_collaboration_flows
  File "/tmp/tmp.L2TH2Y5coc/artifact_tool_v2-2.8.22/artifact_tool/generated/interface/models.py", line 32317, in hydrate_crdt_from_proto
  File "/tmp/tmp.L2TH2Y5coc/artifact_tool_v2-2.8.22/artifact_tool/rpc/remote.py", line 749, in __call__
  File "/tmp/tmp.L2TH2Y5coc/artifact_tool_v2-2.8.22/artifact_tool/rpc/client.py", line 150, in call
artifact_tool.rpc.client.RemoteError: hydrateCrdtFromProto requires an empty collaborative document.

```

This report distinguishes source-code checks from real staging checks. Container/service E2E is not claimed unless actually executed.
