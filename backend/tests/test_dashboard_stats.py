from test_workflow_history import approved_workflow


def test_dashboard_stats_empty(client_with_database):
    data = client_with_database.get('/dashboard/stats').json()
    assert data['total_workflows'] == 0
    assert data['total_executions'] == 0
    assert data['success_rate'] == 0
    assert data['recent_workflows'] == []


def test_dashboard_stats_counts_and_orders_activity(client_with_database):
    client = client_with_database
    first = approved_workflow()
    client.post('/workflows', json=first['workflow'])
    assert client.post('/workflows/execute', json=first).status_code == 200
    failed = approved_workflow()
    failed['workflow']['id'] = 'failed-workflow'
    failed['workflow']['steps'][0]['action'] = 'missing'
    assert client.post('/workflows/execute', json=failed).status_code == 422
    # A valid failing execution is produced by division by zero.
    failed['workflow']['steps'][0] = {'id': 'divide', 'tool': 'calculator', 'action': 'divide', 'inputs': {'a': 1, 'b': 0}}
    assert client.post('/workflows/execute', json=failed).status_code == 200
    data = client.get('/dashboard/stats').json()
    assert data['total_workflows'] == 2
    assert data['total_executions'] == 2
    assert data['successful_executions'] == 1
    assert data['failed_executions'] == 1
    assert data['success_rate'] == 50.0
    assert data['recent_executions'][0]['created_at'] >= data['recent_executions'][1]['created_at']
