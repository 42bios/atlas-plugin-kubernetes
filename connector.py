import json
import os
from pathlib import Path
import runpy
import sys
config_path=Path(os.environ['ADDIN_CONFIG_FILE'])
config=json.loads(config_path.read_text())
credential=os.environ['ADDIN_CREDENTIAL_FILE']
os.environ['RUN_ONCE']='true'
sys.path.insert(0,str(Path(__file__).parent/'worker'))
credentials=json.loads(Path(credential).read_text())
for key,name in [('token','kubernetes_token'),('ca','cluster_ca')]:
 path=config_path.parent/name;path.write_text(credentials[key]);path.chmod(0o600)
os.environ.update(KUBERNETES_URL=config['upstreamUrl'],CLUSTER_NAME=config.get('clusterName','Kubernetes'),KUBERNETES_TOKEN_FILE=str(config_path.parent/'kubernetes_token'),CA_FILE=str(config_path.parent/'cluster_ca'))
runpy.run_path(str(Path(__file__).parent/'worker/runtime.py'),run_name='__main__')
