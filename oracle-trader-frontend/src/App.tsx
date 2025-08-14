// src/App.tsx
import React from 'react';
import { HashRouter as Router, Routes, Route, NavLink } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Box from '@mui/material/Box';
import Drawer from '@mui/material/Drawer';
import List from '@mui/material/List';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import DashboardIcon from '@mui/icons-material/Dashboard';
import SettingsIcon from '@mui/icons-material/Tune';
import HistoryIcon from '@mui/icons-material/History';
import TerminalIcon from '@mui/icons-material/Terminal'; 
import LiveTvIcon from '@mui/icons-material/LiveTv'; // ADDED: Import LiveTvIcon for Analysis Logs
import Typography from '@mui/material/Typography';
import { Divider } from '@mui/material';

// Import pages using new feature-based structure with path aliases
import DashboardPage from '@features/dashboard/DashboardPage';
import BotSettingsPage from '@features/settings/BotSettingsPage';
import TradesLogPage from '@features/trades/TradesLogPage';
import ServerLogPage from '@features/logs/ServerLogPage'; 
import AnalysisLogPage from '@features/analysis/AnalysisLogPage'; // ADDED: Import AnalysisLogPage

const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#03a9f4',
    },
    secondary: {
      main: '#f48fb1',
    },
    background: {
      default: '#121212', 
      paper: '#1e1e1e',
    },
    text: {
      primary: '#e0e0e0',
      secondary: '#b0bec5',
    },
  },
  typography: {
    fontFamily: 'Inter, sans-serif',
    h4: { fontWeight: 700 },
    h5: { fontWeight: 600 },
    h6: { fontWeight: 600 },
  },
  components: {
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
          borderRadius: '12px',
        }
      }
    }
  }
});

const drawerWidth = 250;

const AppLogo = () => (
    <svg width="32" height="32" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M50 0L93.3 25V75L50 100L6.7 75V25L50 0Z" fill="#03a9f4"/>
        <path d="M50 15L84.64 35V65L50 85L15.36 65V35L50 15Z" fill="#1e1e1e"/>
        <path d="M50 21L78.82 38V62L50 79L21.18 62V38L50 21Z" fill="#e0e0e0"/>
    </svg>
);

const navLinkStyle = ({ isActive }: { isActive: boolean }) => ({
    margin: '4px 8px',
    borderRadius: '8px',
    color: isActive ? '#03a9f4' : '#b0bec5',
    backgroundColor: isActive ? 'rgba(3, 169, 244, 0.1)' : 'transparent',
    '&:hover': {
      backgroundColor: 'rgba(255, 255, 255, 0.08)',
    },
    '& .MuiListItemIcon-root': {
        color: isActive ? '#03a9f4' : 'inherit',
    },
});

function App() {
  return (
    <ThemeProvider theme={darkTheme}>
      <Router>
        <Box sx={{ display: 'flex' }}>
          <CssBaseline />
          
          <Drawer
            variant="permanent"
            sx={{
              width: drawerWidth,
              flexShrink: 0,
              [`& .MuiDrawer-paper`]: { 
                  width: drawerWidth, 
                  boxSizing: 'border-box',
                  backgroundColor: 'background.paper',
                  borderRight: '1px solid rgba(255, 255, 255, 0.12)'
              },
            }}
          >
            <Box sx={{ p: 2, display: 'flex', alignItems: 'center', justifyContent: 'center', height: 65, borderBottom: '1px solid rgba(255, 255, 255, 0.12)' }}>
              <AppLogo />
              <Typography variant="h6" component="h1" sx={{ fontWeight: 'bold', ml: 1.5 }}>
                Oracle Bot
              </Typography>
            </Box>
            <List sx={{ pt: 1 }}>
              <ListItemButton component={NavLink} to="/" sx={navLinkStyle} >
                <ListItemIcon><DashboardIcon /></ListItemIcon>
                <ListItemText primary="Dashboard" />
              </ListItemButton>
              <ListItemButton component={NavLink} to="/settings" sx={navLinkStyle}>
                <ListItemIcon><SettingsIcon /></ListItemIcon>
                <ListItemText primary="Settings" />
              </ListItemButton>
              <ListItemButton component={NavLink} to="/trades" sx={navLinkStyle}>
                <ListItemIcon><HistoryIcon /></ListItemIcon>
                <ListItemText primary="Trades Log" />
              </ListItemButton>
              {/* ADDED: New menu item for Server Log */}
              <ListItemButton component={NavLink} to="/server-logs" sx={navLinkStyle}>
                <ListItemIcon><TerminalIcon /></ListItemIcon>
                <ListItemText primary="Server Log" />
              </ListItemButton>
              {/* ADDED: New menu item for Analysis Log */}
              <ListItemButton component={NavLink} to="/analysis-logs" sx={navLinkStyle}>
                <ListItemIcon><LiveTvIcon /></ListItemIcon>
                <ListItemText primary="Analysis Log" />
              </ListItemButton>
            </List>
          </Drawer>
          
          <Box
            component="main"
            sx={{ flexGrow: 1, p: 3, width: { sm: `calc(100% - ${drawerWidth}px)` } }}
          >
            <Routes>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/settings" element={<BotSettingsPage />} />
              <Route path="/trades" element={<TradesLogPage />} />
              {/* ADDED: New route for Server Log page */}
              <Route path="/server-logs" element={<ServerLogPage />} />
              {/* ADDED: New route for Analysis Log page */}
              <Route path="/analysis-logs" element={<AnalysisLogPage />} />
            </Routes>
          </Box>

        </Box>
      </Router>
    </ThemeProvider>
  );
}

export default App;