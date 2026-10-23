import json
from pathlib import Path
from datetime import datetime, timezone
from django.core.management.base import BaseCommand, CommandError
from config.mongodb import get_database
from TradConnect.identities import exact


class Command(BaseCommand):
    help='Consulta o activa las cuentas elegidas; requiere --aplicar para escribir.'
    def add_arguments(self,parser):
        group=parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--todos',action='store_true')
        group.add_argument('--correo',action='append')
        parser.add_argument('--aplicar',action='store_true')
        parser.add_argument('--respaldo',default='respaldos/activacion_usuarios.jsonl')
    def handle(self,*args,**options):
        collection=get_database()['usuarios_empresas_roles']
        scope={} if options['todos'] else {'$or':[{'correo':exact(value)} for value in options['correo']]}
        docs=list(collection.find(scope,{'_id':1,'usuario_id':1,'estado_usuario':1}))
        if not docs: raise CommandError('No se encontraron cuentas para la seleccion.')
        changed=0
        if options['aplicar']:
            path=Path(options['respaldo']).resolve(); path.parent.mkdir(parents=True,exist_ok=True)
            try:
                with path.open('x',encoding='utf-8') as output:
                    from bson import json_util
                    for doc in docs: output.write(json_util.dumps(doc)+'\n')
            except FileExistsError: raise CommandError('El respaldo ya existe; usa otro --respaldo.')
            result=collection.update_many({'_id':{'$in':[doc['_id'] for doc in docs]}},{'$set':{'estado_usuario':True}})
            changed=result.modified_count
        self.stdout.write(json.dumps({'usuarios':len({doc['usuario_id'] for doc in docs}),'vinculos':len(docs),
            'inactivos':sum(doc.get('estado_usuario') is not True for doc in docs),'activados':changed,'aplicado':options['aplicar']}))
