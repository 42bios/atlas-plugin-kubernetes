import importlib.util,json,os,tempfile,unittest,sys
from pathlib import Path
from unittest.mock import patch,MagicMock
PLUGIN=Path(__file__).resolve().parents[1]/'worker/collector.py'
def load(name):
 spec=importlib.util.spec_from_file_location(name,PLUGIN)
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
class CollectorTests(unittest.TestCase):

    def test_kubernetes_ownership_endpoints_and_no_secrets(self):
        m = load('kubernetes')
        resources = {k: [] for k in m.RESOURCES}

        def item(uid, name, namespace=None, **kwargs):
            return {'metadata': dict(uid=uid, name=name, **{'namespace': namespace} if namespace else {}), **kwargs}
        resources['Namespace'] = [item('ns', 'apps')]
        resources['Node'] = [item('node', 'worker')]
        dep = item('dep', 'web', 'apps', spec={'replicas': 2})
        resources['Deployment'] = [dep]
        rs = item('rs', 'web-rs', 'apps')
        rs['metadata']['ownerReferences'] = [{'uid': 'dep', 'controller': True}]
        resources['ReplicaSet'] = [rs]
        pod = item('pod', 'web-pod', 'apps', spec={'nodeName': 'worker', 'containers': [{'name': 'web', 'image': 'nginx', 'env': [{'value': 'SECRET'}]}]})
        pod['metadata']['ownerReferences'] = [{'uid': 'rs', 'controller': True}]
        resources['Pod'] = [pod]
        resources['Service'] = [item('svc', 'web', 'apps', spec={'clusterIPs': ['10.0.0.1']})]
        slice = item('slice', 'web-1', 'apps', endpoints=[{'targetRef': {'uid': 'pod'}}])
        slice['metadata']['labels'] = {'kubernetes.io/service-name': 'web'}
        resources['EndpointSlice'] = [slice]
        result = m.collect(lambda path: {'items': resources[next((k for (k, v) in m.RESOURCES.items() if path.startswith(v + '?')))]}, 'kube-test')
        records = {r['id']: r for r in result['services']}
        self.assertEqual(records['pod']['host'], 'rs')
        self.assertEqual(records['rs']['host'], 'dep')
        self.assertTrue(any((l['type'] == 'Scheduled on' and l['target'] == 'node' for l in result['links'])))
        self.assertTrue(any((l['type'] == 'Routes to' and l['source'] == 'svc' for l in result['links'])))
        self.assertNotIn('SECRET', str(result))
        with self.assertRaises(RuntimeError):
            m.collect(lambda path: (_ for _ in ()).throw(RuntimeError('denied')), 'kube-test')
