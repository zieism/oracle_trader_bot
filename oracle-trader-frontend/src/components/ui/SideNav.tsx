// src/components/SideNav.tsx
import React from 'react';
import { NavLink } from 'react-router-dom';
import Drawer from '@mui/material/Drawer';
import List from '@mui/material/List';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import DashboardIcon from '@mui/icons-material/Dashboard';
import SettingsIcon from '@mui/icons-material/Tune';
import HistoryIcon from '@mui/icons-material/History';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import { Divider } from '@mui/material';

// A simple inline SVG logo as a placeholder
const AppLogo = () => (
    <svg width="32" height="32" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M50 0L93.3 25V75L50 100L6.7 75V25L50 0Z" fill="#03a9f4"/>
        <path d="M50 15L84.64 35V65L50 85L15.36 65V35L50 15Z" fill="#1a1a1a"/>
        <path d="M50 21L78.82 38V62L50 79L21.18 62V38L50 21Z" fill="#e0e0e0"/>
    </svg>
);

interface SideNavProps {
    drawerWidth: number;
}

const SideNav: React.FC<SideNavProps> = ({ drawerWidth }) => {

  const navLinkStyle = ({ isActive }: { isActive: boolean }) => ({
    margin: '4px 8px',
    borderRadius: '8px',
    color: isActive ? '#03a9f4' : '#e0e0e0',
    backgroundColor: isActive ? 'rgba(3, 169, 244, 0.1)' : 'transparent',
    '&:hover': {
      backgroundColor: 'rgba(255, 255, 255, 0.08)',
    },
    '& .MuiListItemIcon-root': {
        color: isActive ? '#03a9f4' : '#b0bec5',
    },
  });

  return (
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
      <Box sx={{ p: 2, display: 'flex', alignItems: 'center', justifyContent: 'center', height: 65 }}>
        <AppLogo />
        <Typography variant="h6" component="h1" sx={{ fontWeight: 'bold', ml: 1.5 }}>
          Oracle Bot
        </Typography>
      </Box>
      <Divider sx={{ borderColor: 'rgba(255, 255, 255, 0.12)' }}/>
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
      </List>
    </Drawer>
  );
};

export default SideNav;
