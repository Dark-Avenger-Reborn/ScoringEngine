// Connect to Socket.IO server and render a stacked vertical bar chart
// Expects a `scores` object like: { team1: { ubuntu1ping: {score: 0}, ... }, team2: {...} }

(function () {
  // Load socket.io from the default namespace
  const socket = io();

  // Helpers to map service keys to friendly labels and colors
  const serviceOrder = [
    'ubuntu1ping', 'ubuntu2ping',
    'ubuntu1ssh', 'ubuntu2ssh',
    'ubuntu1web', 'ubuntu2web'
  ];

  const serviceLabels = {
    ubuntu1ping: 'Ping (1)',
    ubuntu2ping: 'Ping (2)',
    ubuntu1ssh: 'SSH (1)',
    ubuntu2ssh: 'SSH (2)',
    ubuntu1web: 'Web (1)',
    ubuntu2web: 'Web (2)'
  };

  const colors = [
    '#4dc9f6', '#f67019', '#f53794', '#537bc4', '#acc236', '#166a8f'
  ];

  // Create datasets template for Chart.js
  function makeDatasets() {
    return serviceOrder.map((key, idx) => ({
      label: serviceLabels[key] || key,
      backgroundColor: colors[idx % colors.length],
      data: []
    }));
  }

  // Build chart
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

  const leaderboardChart = new Chart(ctx, chartConfig);

  function updateChartFromScores(scores) {
    // teams sorted by name
    const teams = Object.keys(scores).sort();

    // Reset labels and data
    leaderboardChart.data.labels = teams;
    leaderboardChart.data.datasets.forEach(ds => ds.data = []);

    teams.forEach(team => {
      serviceOrder.forEach((svc, idx) => {
        const scoreObj = scores[team][svc];
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

})();
