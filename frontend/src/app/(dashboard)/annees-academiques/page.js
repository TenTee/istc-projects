'use client';

import React from 'react';
import { Box, Typography } from '@mui/material';
import EventNoteIcon from '@mui/icons-material/EventNote';
import AnneesAcademiquesPanel from '../../../components/academique/AnneesAcademiquesPanel';

/** Années académiques : accessible avec la Pédagogie (lecture) ou le droit « Gérer les années académiques ». */
export default function AnneesAcademiquesPage() {
  return (
    <Box>
      <Typography variant="h5" fontWeight="bold" color="primary" sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
        <EventNoteIcon /> Années académiques
      </Typography>
      <AnneesAcademiquesPanel />
    </Box>
  );
}
