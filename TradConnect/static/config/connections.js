(() => {
    const root = document.querySelector('[data-endpoint]');
    const button = document.getElementById('refreshConnections');
    const status = document.getElementById('connectionStatus');
    const labels = {login_url:'Inicio de sesión (POST)',marketplace_url:'Marketplace',nosql_orders_url:'Pedidos MongoDB (JWT)',configuration_url:'Configuración',connections_url:'Estado JSON'};
    async function refresh() {
        button.disabled = true; status.textContent = 'Comprobando conexiones…';
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 15000);
        try {
            const response = await fetch(root.dataset.endpoint, {headers:{Accept:'application/json'},cache:'no-store',signal:controller.signal});
            const data = await response.json();
            if (!data.databases || !data.links) throw Error('Respuesta inesperada del servidor.');
            document.getElementById('baseUrl').textContent = data.links.api_base_url;
            for (const [name, prefix] of [['sql','sql'],['mongodb','mongo']]) {
                const result = data.databases[name];
                const state = document.getElementById(prefix+'State');
                state.textContent = result.ready ? 'Disponible' : result.connected ? 'Conectada; configuración pendiente' : 'No disponible';
                state.className = result.ready ? 'ready' : 'unavailable';
                document.getElementById(prefix+'Message').textContent = result.message;
            }
            const links = document.getElementById('connectionLinks'); links.replaceChildren();
            for (const [key,label] of Object.entries(labels)) {
                const term = document.createElement('dt'), description = document.createElement('dd'), link = document.createElement('a');
                term.textContent = label; link.textContent = data.links[key]; link.href = data.links[key];
                description.append(link); links.append(term,description);
            }
            status.textContent = (data.status === 'ok' ? 'Ambas bases disponibles.' : 'Hay una conexión pendiente de revisar.') + ' Comprobado: ' + new Date(data.checked_at).toLocaleString('es-NI');
        } catch (error) {
            status.textContent = error.name === 'AbortError' ? 'La comprobación tard? demasiado. Reintenta.' : 'No se pudo consultar el estado. Comprueba que Django está iniciado.';
        } finally { clearTimeout(timer); button.disabled = false; }
    }
    button.addEventListener('click', refresh); refresh();
})();
