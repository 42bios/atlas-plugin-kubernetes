import importlib.util, unittest
from urllib.parse import urlsplit,parse_qs
from pathlib import Path
s=importlib.util.spec_from_file_location('kube_variants',Path(__file__).resolve().parents[1]/'worker/collector.py');c=importlib.util.module_from_spec(s);s.loader.exec_module(c)
def item(uid,name,ns=None,**kwargs):return {'metadata':dict(uid=uid,name=name,**({'namespace':ns} if ns else {})),**kwargs}
class Variations(unittest.TestCase):
 def collect(self,resources):return c.collect(lambda p:{'items':resources.get(urlsplit(p).path,[])},'test')
 def test_paginated_namespaces_and_encoded_cursor(self):
  seen=[]
  def get(path):
   query=parse_qs(urlsplit(path).query);seen.append(path)
   if urlsplit(path).path==c.RESOURCES['Namespace']:
    return {'items':[item('ns2','second')]} if query.get('continue')==['a+b/='] else {'items':[item('ns1','first')],'metadata':{'continue':'a+b/='}}
   return {'items':[]}
  result=c.collect(get,'test');self.assertEqual(len(result['services']),3);self.assertTrue(any('a%2Bb%2F%3D' in p for p in seen))
 def test_repeated_cursor_and_bad_page_rejected(self):
  with self.assertRaisesRegex(ValueError,'Repeated'):c.collect(lambda _:{'items':[],'metadata':{'continue':'same'}},'test')
  for page in (None,[],{'items':{}},{'items':None}):
   with self.assertRaisesRegex(ValueError,'Invalid'):c.collect(lambda _:page,'test')
 def test_pending_pod_has_no_fabricated_node(self):
  r=self.collect({c.RESOURCES['Pod']:[item('pod','pending','apps',spec={'containers':[]})]})
  self.assertFalse(any(l['type']=='Scheduled on' for l in r['links']))
 def test_ingress_namespace_isolation_and_duplicate_endpoint_slices(self):
  resources={c.RESOURCES['Service']:[item('s1','web','a'),item('s2','web','b')],c.RESOURCES['Pod']:[item('p','pod','a')],c.RESOURCES['Ingress']:[item('i','ingress','a',spec={'defaultBackend':{'service':{'name':'web'}}})],c.RESOURCES['EndpointSlice']:[item('e1','one','a',endpoints=[{'targetRef':{'uid':'p'}}]),item('e2','two','a',endpoints=[{'targetRef':{'uid':'p'}}])]}
  for endpoint in resources[c.RESOURCES['EndpointSlice']]:endpoint['metadata']['labels']={'kubernetes.io/service-name':'web'}
  r=self.collect(resources);self.assertEqual(sum(l['source']=='s1' and l['target']=='p' for l in r['links']),1);self.assertTrue(any(l['source']=='i' and l['target']=='s1' for l in r['links']));self.assertFalse(any(l['target']=='s2' for l in r['links']))
 def test_init_container_storage_and_resource_ips_not_global_assignments(self):
  pod=item('pod','web','apps',spec={'initContainers':[{'name':'init','image':'alpine','env':[{'value':'NEVER_EXPORT'}]}],'volumes':[{'persistentVolumeClaim':{'claimName':'data'}}]},status={'podIPs':[{'ip':'10.0.0.2'}]})
  r=self.collect({c.RESOURCES['Pod']:[pod],c.RESOURCES['PersistentVolumeClaim']:[item('pvc','data','apps')]})
  self.assertTrue(any(l['type']=='Uses storage' and l['target']=='pvc' for l in r['links']));self.assertTrue(any(s['id']=='pod-container-init' for s in r['services']));self.assertNotIn('NEVER_EXPORT',str(r));self.assertTrue(all('ip' not in s for s in r['services']))
