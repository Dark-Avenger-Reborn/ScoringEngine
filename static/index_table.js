// Render a teams x systems status table and update it on 'scores' socket events.
(function () {
  const socket = io();

  let systemsList = [];
  let servicesConfig = {};
  let serviceOrder = [];
  let serviceLabels = {};

  // Fetch systems configuration from API
  async function loadSystemsConfig() {
    try {
      const res = await fetch('/api/systems');
      if (!res.ok) throw new Error('Failed to load systems');
      const data = await res.json();
      systemsList = data.systems || [];
      servicesConfig = data.services || {};
      
      // Build service order and labels dynamically
      serviceOrder = [];
      serviceLabels = {};
      systemsList.forEach(system => {
        system.services.forEach(serviceName => {
          const key = `${system.name}${serviceName}`;
          serviceOrder.push(key);
          const serviceConfig = servicesConfig[serviceName] || {};
          const systemNum = system.name.replace(/\D/g, '') || '?';
          serviceLabels[key] = `${serviceConfig.display_name || serviceName} (${systemNum})`;
        });
      });
    } catch (err) {
      console.error('Failed to load systems config:', err);
      // Fallback to hardcoded defaults if API fails
      serviceOrder = [
        'ubuntu1ping', 'ubuntu2ping',
        'ubuntu1ssh', 'ubuntu2ssh',
        'ubuntu1web', 'ubuntu2web'
      ];
      serviceLabels = {
        ubuntu1ping: 'Ping (1)',
        ubuntu2ping: 'Ping (2)',
        ubuntu1ssh: 'SSH (1)',
        ubuntu2ssh: 'SSH (2)',
        ubuntu1web: 'Web (1)',
        ubuntu2web: 'Web (2)'
      };
    }
  }

  function makeTable(scores) {
    const container = document.getElementById('tableContainer');
    container.innerHTML = '';

    const table = document.createElement('table');
    const caption = document.createElement('caption');
    caption.textContent = 'Teams vs Systems — green = success';
    table.appendChild(caption);

    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');
    const emptyTh = document.createElement('th');
    emptyTh.textContent = 'Team';
    headerRow.appendChild(emptyTh);

    serviceOrder.forEach(svc => {
      const th = document.createElement('th');
      th.textContent = serviceLabels[svc] || svc;
      headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    const tbody = document.createElement('tbody');

    const teams = Object.keys(scores).sort();
    teams.forEach(team => {
      const row = document.createElement('tr');
      const teamCell = document.createElement('th');
      teamCell.textContent = team;
      row.appendChild(teamCell);

      serviceOrder.forEach(svc => {
        const td = document.createElement('td');
        const svcObj = scores[team] && scores[team][svc];
        const err = svcObj ? svcObj.error : 'Not tested';
        td.setAttribute('data-service', svc);
        td.setAttribute('data-team', team);

        if (err === 'Success') {
          td.className = 'ok';
          td.textContent = 'OK';
        } else if (err === 'Not tested') {
          td.className = 'unknown';
          td.textContent = 'Not tested';
        } else {
          // Hide error details on front page; just show FAIL without tooltip
          td.className = 'fail';
          td.textContent = 'FAIL';
        }

        row.appendChild(td);
      });

      tbody.appendChild(row);
    });

    table.appendChild(tbody);
    container.appendChild(table);
  }

  function updateTableFromScores(scores) {
    // If table doesn't exist yet, build it
    const container = document.getElementById('tableContainer');
    if (!container) return;

    // If there is no table yet, build fully
    if (!container.querySelector('table')) {
      makeTable(scores);
      return;
    }

    // Otherwise, update cells in place
    const teams = Object.keys(scores).sort();
    teams.forEach(team => {
      serviceOrder.forEach(svc => {
        const selector = `td[data-team="${team}"][data-service="${svc}"]`;
        const td = container.querySelector(selector);
        const svcObj = scores[team] && scores[team][svc];
        const err = svcObj ? svcObj.error : 'Not tested';
        if (!td) return;
        if (err === 'Success') {
          td.className = 'ok';
          td.textContent = 'OK';
          td.removeAttribute('title');
        } else if (err === 'Not tested') {
          td.className = 'unknown';
          td.textContent = 'Not tested';
          td.removeAttribute('title');
        } else {
          // Hide error details on front page; just show FAIL without tooltip
          td.className = 'fail';
          td.textContent = 'FAIL';
          td.removeAttribute('title');
        }
      });
    });
  }

  // On connect receive initial scores through socket as in leaderboard.js
  socket.on('scores', function (scores) {
    try {
      // If no table exists, build it; else update
      updateTableFromScores(scores);
    } catch (err) {
      console.error('Error updating table from scores', err);
      if (window.AppNotice) AppNotice.error('Failed to update leaderboard table from scores.');
    }
  });

  socket.on('connect', function () {
    console.log('Connected to scoreboard socket');
    // Also attempt a one-time fetch of scores.json for environments where
    // the socket event might not arrive (e.g., static preview).
    fetch('/scores.json').then(r => {
      if (!r.ok) return null;
      return r.json();
    }).then(data => {
      if (data) updateTableFromScores(data);
    }).catch((e) => {
      console.warn('Initial scores fetch failed', e);
      if (window.AppNotice) AppNotice.warn('Could not load initial scores. Waiting for live updates...');
    });
  });

  socket.on('disconnect', function (){
    if (window.AppNotice) AppNotice.warn('Disconnected from live updates. Attempting to reconnect...');
  });

  // Initialize by loading systems config first
  loadSystemsConfig().then(() => {
    // Try to fetch initial scores
    fetch('/scores.json').then(r => {
      if (!r.ok) return null;
      return r.json();
    }).then(data => {
      if (data) updateTableFromScores(data);
    }).catch(() => {});
  });

})();
