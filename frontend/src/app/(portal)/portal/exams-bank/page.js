"use client";

import React, { useEffect, useState } from 'react';
import { Box, Button, Card, CardContent, Chip, Dialog, DialogActions, DialogContent, DialogTitle, Grid, Typography, CircularProgress, useTheme, useMediaQuery } from '@mui/material';
import VisibilityIcon from '@mui/icons-material/Visibility';
import { epreuvesService } from '../../../../services/api/services';
import { getMediaUrl } from '../../../../services/api/client';

function toList(data) {
  return Array.isArray(data) ? data : data?.results || [];
}

export default function ExamsBankStudentPage() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [previewDialog, setPreviewDialog] = useState({ open: false, url: '', title: '' });
  const theme = useTheme();
  const fullScreen = useMediaQuery(theme.breakpoints.down('sm'));

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const res = await epreuvesService.list({ student_view: true });
        if (!mounted) return;
        setItems(toList(res));
      } catch (e) {
        console.error(e);
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => (mounted = false);
  }, []);

  const download = (filePath) => {
    if (!filePath) return;
    window.open(getMediaUrl(filePath), '_blank');
  };

  const handlePreview = (filePath, title) => {
    if (!filePath) return;
    setPreviewDialog({ open: true, url: getMediaUrl(filePath), title });
  };

  if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box>;

  return (
    <Box sx={{ p: { xs: 0, sm: 2, md: 3 } }}>
      <Typography variant="h5" sx={{ mb: 2 }}>Banque d&apos;épreuves (Étudiants)</Typography>
      <Grid container spacing={2}>
        {items.map((it) => (
          <Grid item xs={12} sm={6} md={4} key={it.id}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 1, mb: 1 }}>
                  <Typography variant="subtitle1" sx={{ minWidth: 0, wordBreak: 'break-word' }}>{it.nom}</Typography>
                  <Chip label={it.type_epreuve} size="small" sx={{ flexShrink: 0 }} />
                </Box>
                <Typography variant="body2" color="text.secondary">{it.module_nom} — {it.filiere_nom} / {it.niveau_nom}</Typography>
                <Typography variant="caption" display="block">Auteur: {it.auteur || '-' } — {it.annee_academique_libelle}</Typography>
                <Box sx={{ mt: 2, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  <Button size="small" startIcon={<VisibilityIcon />} variant="outlined" onClick={() => handlePreview(it.fichier, `Sujet — ${it.nom}`)} disabled={!it.fichier}>
                    Voir Sujet
                  </Button>
                  <Button size="small" startIcon={<VisibilityIcon />} variant="outlined" color="success" onClick={() => handlePreview(it.corrige, `Corrigé — ${it.nom}`)} disabled={!it.corrige}>
                    Voir Corrigé
                  </Button>
                  <Button size="small" onClick={() => download(it.fichier)} disabled={!it.fichier}>Télécharger Sujet</Button>
                  <Button size="small" onClick={() => download(it.corrige)} disabled={!it.corrige}>Télécharger Corrigé</Button>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Dialog open={previewDialog.open} onClose={() => setPreviewDialog({ open: false, url: '', title: '' })} maxWidth="lg" fullWidth fullScreen={fullScreen}>
        <DialogTitle sx={{ wordBreak: 'break-word' }}>{previewDialog.title}</DialogTitle>
        <DialogContent sx={{ p: 0, height: { xs: 'calc(100dvh - 140px)', sm: '75vh' } }}>
          {previewDialog.url && (
            <iframe
              src={previewDialog.url}
              style={{ width: '100%', height: '100%', border: 'none' }}
              title={previewDialog.title}
            />
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => download(previewDialog.url)} variant="outlined">
            Télécharger
          </Button>
          <Button onClick={() => setPreviewDialog({ open: false, url: '', title: '' })} variant="contained">
            Fermer
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
