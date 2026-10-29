"""Check the optional OpenBB V5 namespace without reading or changing user configuration."""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

with tempfile.TemporaryDirectory(prefix='banksonsale-openbb-') as directory:
    with patch('pathlib.Path.home', return_value=Path(directory)):
        from openbb import obb
        result = obb.banksonsale.sample(cert=58665)
        assert len(result.results) == 8
        assert result.extra['banksonsale']['publisher'] == 'BanksOnSale'
        assert result.extra['banksonsale']['metric_definitions']['cet1_ratio_pct']['source_field'] == 'RBCT1CER'
        assert len(result.to_dataframe()) == 8
        definitions = obb.banksonsale.definitions()
        assert len(definitions.results) == 14
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from openbb_banksonsale.router import router
        app = FastAPI()
        app.include_router(router.api_router, prefix='/api/v1/banksonsale')
        response = TestClient(app).get('/api/v1/banksonsale/sample', params={'cert':58665})
        assert response.status_code == 200, response.text
        rest = response.json()
        assert len(rest['results']) == 8
        assert rest['extra']['banksonsale']['dataset_id'] == result.extra['banksonsale']['dataset_id']
        print(json.dumps({'openbb_namespace':'obb.banksonsale','offline_rows':len(result.results),'definitions':len(definitions.results),'dataframe_rows':len(result.to_dataframe()),'rest_status':response.status_code,'python_rest_agreement':True}))
