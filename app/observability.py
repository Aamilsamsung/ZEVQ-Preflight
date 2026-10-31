"""Request diagnostics without source, credentials, query text or URL parameters."""
from contextvars import ContextVar
import json
import logging
import time
import uuid
from sqlalchemy import event

metrics=ContextVar('preflight_request_metrics',default=None)
log=logging.getLogger('uvicorn.error')


def instrument_engine(engine):
    @event.listens_for(engine,'do_connect')
    def connecting(dialect,record,args,kwargs):record.info['_preflight_connect_started']=time.perf_counter()
    @event.listens_for(engine,'connect')
    def connected(connection,record):
        current=metrics.get();started=record.info.pop('_preflight_connect_started',None)
        if current is not None and started is not None:current['connect_ms']+=(time.perf_counter()-started)*1000
    @event.listens_for(engine,'before_cursor_execute')
    def before(conn,cursor,statement,parameters,context,executemany):
        current=metrics.get()
        if current is not None:context._preflight_started=time.perf_counter()
    @event.listens_for(engine,'after_cursor_execute')
    def after(conn,cursor,statement,parameters,context,executemany):
        current=metrics.get();started=getattr(context,'_preflight_started',None)
        if current is not None and started is not None:
            current['queries']+=1;current['db_ms']+=(time.perf_counter()-started)*1000


class RequestDiagnostics:
    def __init__(self,app):self.app=app
    async def __call__(self,scope,receive,send):
        if scope['type']!='http':return await self.app(scope,receive,send)
        request_id=uuid.uuid4().hex;scope['preflight_request_id']=request_id;started=time.perf_counter();data={'queries':0,'db_ms':0.0,'connect_ms':0.0};token=metrics.set(data);status=500
        async def send_with_diagnostics(message):
            nonlocal status
            if message['type']=='http.response.start':
                status=message['status'];headers=list(message.get('headers',[]))
                headers.extend([(b'x-request-id',request_id.encode()),(b'server-timing',('app;dur=%.2f, db;dur=%.2f, connect;dur=%.2f'%(1000*(time.perf_counter()-started),data['db_ms'],data['connect_ms'])).encode())]);message={**message,'headers':headers}
            await send(message)
        try:await self.app(scope,receive,send_with_diagnostics)
        finally:
            route=getattr(scope.get('route'),'path',None) or 'unmatched'
            # Only allowlisted method/route template and numeric measurements; no request bodies, headers, URLs or exceptions.
            method=scope.get('method','')
            if method not in ('GET','POST','PUT','PATCH','DELETE','HEAD','OPTIONS'):method='OTHER'
            log.info(json.dumps({'event':'http_request','request_id':request_id,'method':method,'route':route,'status':status,'duration_ms':round((time.perf_counter()-started)*1000,2),'db_ms':round(data['db_ms'],2),'connect_ms':round(data['connect_ms'],2),'queries':data['queries']},sort_keys=True))
            metrics.reset(token)
