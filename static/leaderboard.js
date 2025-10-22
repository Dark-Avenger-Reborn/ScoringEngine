// Connect to Socket.IO server and render a stacked vertical bar chart
// Expects a `scores` object like: { team1: { ubuntu1ping: {score: 0}, ... }, team2: {...} }

(function () {
  // Load socket.io from the default namespace
  const socket = io();

  let systemsList = [];
  let servicesConfig = {};
  let serviceOrder = [];
  let serviceLabels = {};
  let leaderboardChart = null;

  const colors = [
    '#4dc9f6', '#f67019', '#f53794', '#537bc4', '#acc236', '#166a8f',
    '#8549ba', '#00d8ff', '#ff6384', '#36a2eb', '#ffce56', '#4bc0c0'
  ];

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

  // Create datasets template for Chart.js
  function makeDatasets() {
    return serviceOrder.map((key, idx) => ({
      label: serviceLabels[key] || key,
      backgroundColor: colors[idx % colors.length],
      data: []
    }));
  }

  // Build chart
  function initChart() {
    const ctx = document.getElementById('leaderboardChart').getContext('2d');
    const chartConfig = {
      type: 'bar',
      data: {
        labels: [], // team names
        datasets: makeDatasets()
      },
      options: {
        responsive: true,
        plugins: {
          legend: { position: 'top' }
        },
        scales: {
          x: { stacked: true },
          y: { stacked: true, beginAtZero: true }
        }
      }
    };

    leaderboardChart = new Chart(ctx, chartConfig);
  }

  function updateChartFromScores(scores) {
    if (!leaderboardChart) return;
    
    // teams sorted by name
    const teams = Object.keys(scores).sort();

    // Reset labels and data
    leaderboardChart.data.labels = teams;
    leaderboardChart.data.datasets.forEach(ds => ds.data = []);

    teams.forEach(team => {
      serviceOrder.forEach((svc, idx) => {
        const scoreObj = scores[team] ? scores[team][svc] : null;
        const pts = scoreObj ? (scoreObj.score || 0) : 0;
        leaderboardChart.data.datasets[idx].data.push(pts);
      });
    });

    leaderboardChart.update();
  }

  // Receive initial scores on connect (server emits when a client connects)
  socket.on('scores', function (scores) {
    console.log('Received scores update', scores);
    try {
      updateChartFromScores(scores);
    } catch (err) {
      console.error('Error updating chart from scores', err);
      if (window.AppNotice) AppNotice.error('Failed to update leaderboard chart from scores.');
    }
  });

  // Also listen for live broadcasts that update scores
  // (same event name used by server)
  socket.on('connect', function () {
    console.log('Connected to scoreboard socket');
  });

  socket.on('disconnect', function (){
    if (window.AppNotice) AppNotice.warn('Disconnected from live updates. Attempting to reconnect...');
  });

  // Initialize by loading systems config and building chart
  loadSystemsConfig().then(() => {
    initChart();
    // Try to fetch initial scores
    fetch('/scores.json').then(r => {
      if (!r.ok) return null;
      return r.json();
    }).then(data => {
      if (data) updateChartFromScores(data);
    }).catch(() => {});
  });

})();
