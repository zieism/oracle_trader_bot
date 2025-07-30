<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Infographic: KuCoin Futures Automated Trader Bot</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Inter', sans-serif;
            background-color: #f0f2f5;
        }
        .chart-container {
            position: relative;
            width: 100%;
            max-width: 600px;
            margin-left: auto;
            margin-right: auto;
            height: 350px;
            max-height: 400px;
        }
        @media (max-width: 768px) {
            .chart-container {
                height: 300px;
                max-height: 350px;
            }
        }
        .flowchart-arrow {
            font-size: 2rem;
            line-height: 1;
            color: #7a5195;
        }
    </style>
</head>
<body class="text-gray-800">

    <div class="container mx-auto p-4 md:p-8 max-w-7xl">

        <header class="text-center mb-12">
            <h1 class="text-4xl md:text-5xl font-extrabold text-[#003f5c] mb-2">KuCoin Futures Automated Trader Bot</h1>
            <p class="text-lg text-gray-600">A Technical Overview of a Full-Stack Trading Solution</p>
        </header>

        <main class="space-y-12">
            
            <section id="features">
                <h2 class="text-3xl font-bold text-center mb-8 text-[#003f5c]">Core Features at a Glance</h2>
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 text-center">
                    <div class="bg-white rounded-lg shadow-md p-6">
                        <div class="text-6xl font-extrabold text-[#ff764a]">2</div>
                        <h3 class="text-xl font-semibold mt-2">Trading Strategies</h3>
                        <p class="text-gray-600 mt-1">Implements both Trend-Following and Range-Trading algorithms.</p>
                    </div>
                    <div class="bg-white rounded-lg shadow-md p-6">
                        <div class="text-6xl font-extrabold text-[#ef5675]">DB</div>
                        <h3 class="text-xl font-semibold mt-2">Persistent Storage</h3>
                        <p class="text-gray-600 mt-1">Utilizes PostgreSQL to log every trade, status, and PNL for analysis.</p>
                    </div>
                    <div class="bg-white rounded-lg shadow-md p-6">
                        <div class="text-6xl font-extrabold text-[#bc5090]">UI</div>
                        <h3 class="text-xl font-semibold mt-2">Full UI Control</h3>
                        <p class="text-gray-600 mt-1">A comprehensive React dashboard for monitoring, configuration, and control.</p>
                    </div>
                    <div class="bg-white rounded-lg shadow-md p-6">
                        <div class="text-6xl font-extrabold text-[#7a5195]">API</div>
                        <h3 class="text-xl font-semibold mt-2">Powerful API</h3>
                        <p class="text-gray-600 mt-1">Built on FastAPI, providing robust endpoints for all bot functions.</p>
                    </div>
                </div>
            </section>
            
            <section id="tech-stack">
                <h2 class="text-3xl font-bold text-center mb-8 text-[#003f5c]">The Technology Stack</h2>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
                    <div class="bg-white rounded-lg shadow-md p-6">
                        <h3 class="text-2xl font-bold mb-4 text-center text-[#374c80]">Backend Technologies</h3>
                        <p class="text-center text-gray-600 mb-4">The engine room of the bot, built for performance and reliability.</p>
                        <div class="chart-container h-96">
                            <canvas id="backendTechChart"></canvas>
                        </div>
                    </div>
                    <div class="bg-white rounded-lg shadow-md p-6">
                        <h3 class="text-2xl font-bold mb-4 text-center text-[#374c80]">Frontend Technologies</h3>
                        <p class="text-center text-gray-600 mb-4">Crafting an intuitive and responsive user experience for full control.</p>
                        <div class="chart-container h-96">
                            <canvas id="frontendTechChart"></canvas>
                        </div>
                    </div>
                </div>
            </section>

            <section id="architecture">
                <h2 class="text-3xl font-bold text-center mb-8 text-[#003f5c]">System Architecture Flow</h2>
                <div class="bg-white rounded-lg shadow-md p-6 md:p-8">
                    <p class="text-center text-gray-600 mb-8">The system is designed with a clear separation of concerns, from user interaction to trade execution, all orchestrated through a secure reverse proxy.</p>
                    <div class="flex flex-col items-center space-y-4 md:flex-row md:space-y-0 md:space-x-4 md:justify-center md:items-stretch">
                        
                        <div class="flex flex-col items-center text-center">
                            <div class="bg-[#ffa600] text-white rounded-full w-24 h-24 flex items-center justify-center text-4xl font-bold">👤</div>
                            <h4 class="font-bold mt-2">User</h4>
                        </div>
                        
                        <div class="flex items-center flowchart-arrow transform md:rotate-0 rotate-90">→</div>

                        <div class="flex flex-col items-center text-center">
                            <div class="bg-[#ff764a] text-white rounded-lg p-4 w-32 h-24 flex items-center justify-center">
                                <span class="font-bold">Nginx<br/>Proxy</span>
                            </div>
                            <h4 class="font-bold mt-2">Gateway</h4>
                        </div>
                        
                        <div class="flex items-center flowchart-arrow transform md:rotate-0 rotate-90">→</div>
                        
                        <div class="border-2 border-dashed border-[#7a5195] rounded-lg p-4 flex flex-col md:flex-row gap-4">
                             <div class="flex flex-col items-center text-center">
                                <div class="bg-[#ef5675] text-white rounded-lg p-4 w-32 h-24 flex items-center justify-center">
                                    <span class="font-bold">React UI<br/>(Vite)</span>
                                </div>
                                <h4 class="font-bold mt-2">Frontend</h4>
                            </div>
                            <div class="flex flex-col items-center text-center">
                                <div class="bg-[#bc5090] text-white rounded-lg p-4 w-32 h-24 flex items-center justify-center">
                                    <span class="font-bold">FastAPI<br/>Backend</span>
                                </div>
                                <h4 class="font-bold mt-2">Backend</h4>
                            </div>
                        </div>

                        <div class="flex items-center flowchart-arrow transform md:rotate-0 rotate-90">→</div>

                        <div class="flex flex-col items-center text-center">
                            <div class="bg-[#374c80] text-white rounded-lg p-4 w-32 h-24 flex items-center justify-center">
                                <span class="font-bold">Bot Engine<br/>(Python)</span>
                            </div>
                            <h4 class="font-bold mt-2">Core Logic</h4>
                        </div>

                        <div class="flex items-center flowchart-arrow transform md:rotate-0 rotate-90">→</div>

                        <div class="flex flex-col items-center text-center">
                            <div class="bg-[#003f5c] text-white rounded-full w-24 h-24 flex items-center justify-center text-3xl font-bold">📈</div>
                            <h4 class="font-bold mt-2">KuCoin API</h4>
                        </div>
                    </div>
                </div>
            </section>

            <section id="capabilities">
                <h2 class="text-3xl font-bold text-center mb-8 text-[#003f5c]">Bot Capabilities Profile</h2>
                <div class="bg-white rounded-lg shadow-md p-6">
                    <p class="text-center text-gray-600 mb-4">A breakdown of the bot's key attributes, showcasing a balanced and robust design.</p>
                    <div class="chart-container h-[400px] max-h-[450px]">
                        <canvas id="capabilitiesRadarChart"></canvas>
                    </div>
                </div>
            </section>

        </main>

        <footer class="text-center mt-12 pt-8 border-t border-gray-300">
            <p class="text-gray-600">Infographic generated based on the project's technical documentation.</p>
        </footer>

    </div>

    <script>
        const colorPalette = {
            primary: '#003f5c',
            secondary: '#374c80',
            tertiary: '#7a5195',
            accent1: '#bc5090',
            accent2: '#ef5675',
            accent3: '#ff764a',
            accent4: '#ffa600'
        };

        const chartColors = Object.values(colorPalette);

        const wrapLabel = (label, maxWidth = 16) => {
            if (label.length <= maxWidth) {
                return label;
            }
            const words = label.split(' ');
            const lines = [];
            let currentLine = '';
            for (const word of words) {
                if ((currentLine + ' ' + word).trim().length > maxWidth) {
                    lines.push(currentLine.trim());
                    currentLine = word;
                } else {
                    currentLine = (currentLine + ' ' + word).trim();
                }
            }
            if (currentLine) {
                lines.push(currentLine.trim());
            }
            return lines;
        };
        
        const tooltipTitleCallback = (tooltipItems) => {
            const item = tooltipItems[0];
            let label = item.chart.data.labels[item.dataIndex];
            if (Array.isArray(label)) {
              return label.join(' ');
            } else {
              return label;
            }
        };

        const defaultChartOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        font: {
                            size: 14,
                            family: 'Inter'
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        title: tooltipTitleCallback
                    },
                    bodyFont: {
                        size: 14,
                        family: 'Inter'
                    },
                    titleFont: {
                        size: 16,
                        family: 'Inter'
                    }
                }
            },
            scales: {
                x: {
                    ticks: {
                        font: { size: 12, family: 'Inter' }
                    }
                },
                y: {
                    ticks: {
                        font: { size: 12, family: 'Inter' }
                    }
                }
            }
        };

        const backendTechData = {
            labels: ['Python 3.9+', 'FastAPI', 'SQLAlchemy', 'PostgreSQL', 'CCXT', 'Pandas & NumPy'].map(l => wrapLabel(l)),
            datasets: [{
                label: 'Backend Stack',
                data: [10, 9, 8, 7, 9, 8],
                backgroundColor: [colorPalette.primary, colorPalette.secondary, colorPalette.tertiary, colorPalette.accent1, colorPalette.accent2, colorPalette.accent3],
                borderColor: 'rgba(255, 255, 255, 0.8)',
                borderWidth: 1
            }]
        };

        new Chart(document.getElementById('backendTechChart'), {
            type: 'bar',
            data: backendTechData,
            options: { ...defaultChartOptions,
                indexAxis: 'y',
                plugins: { ...defaultChartOptions.plugins, legend: { display: false } },
                scales: {
                    x: { display: false },
                    y: {
                        ticks: { font: { size: 14, family: 'Inter', weight: '500' } }
                    }
                }
            }
        });

        const frontendTechData = {
            labels: ['React.js (Vite)', 'TypeScript', 'Material-UI (MUI)', 'Axios', 'React Router DOM'].map(l => wrapLabel(l)),
            datasets: [{
                label: 'Frontend Stack',
                data: [10, 9, 8, 7, 7],
                backgroundColor: [colorPalette.accent4, colorPalette.accent3, colorPalette.accent2, colorPalette.accent1, colorPalette.tertiary],
                borderColor: 'rgba(255, 255, 255, 0.8)',
                borderWidth: 1
            }]
        };

        new Chart(document.getElementById('frontendTechChart'), {
            type: 'bar',
            data: frontendTechData,
            options: { ...defaultChartOptions,
                indexAxis: 'y',
                plugins: { ...defaultChartOptions.plugins, legend: { display: false } },
                scales: {
                    x: { display: false },
                    y: {
                        ticks: { font: { size: 14, family: 'Inter', weight: '500' } }
                    }
                }
            }
        });

        const capabilitiesData = {
            labels: ['Performance', 'Modularity', 'Security', 'Scalability', 'Usability', 'Automation'],
            datasets: [{
                label: 'Bot Profile Score',
                data: [90, 85, 75, 80, 95, 100],
                fill: true,
                backgroundColor: 'rgba(55, 76, 128, 0.2)',
                borderColor: colorPalette.secondary,
                pointBackgroundColor: colorPalette.secondary,
                pointBorderColor: '#fff',
                pointHoverBackgroundColor: '#fff',
                pointHoverBorderColor: colorPalette.secondary
            }]
        };

        new Chart(document.getElementById('capabilitiesRadarChart'), {
            type: 'radar',
            data: capabilitiesData,
            options: { ...defaultChartOptions,
                scales: {
                    r: {
                        angleLines: { color: 'rgba(0, 0, 0, 0.1)' },
                        grid: { color: 'rgba(0, 0, 0, 0.1)' },
                        pointLabels: { font: { size: 14, family: 'Inter' } },
                        ticks: { backdropColor: 'transparent', color: '#666' }
                    }
                }
            }
        });
    </script>

</body>
</html>
