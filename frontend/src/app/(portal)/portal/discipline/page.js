'use client';

import React, { useEffect, useState } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  CircularProgress,
  Chip,
  Alert,
  Divider,
} from '@mui/material';
import GavelIcon from '@mui/icons-material/Gavel';
import { etudiantsService } from '../../../../services/api/services';

export default function StudentDiscipline() {
  const [student, setStudent] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDiscipline = async () => {
      try {
        const res = await etudiantsService.me();
        setStudent(res);
      } catch (error) {
        console.error("Erreur discipline:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchDiscipline();
  }, []);

  if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', mt: 5 }}><CircularProgress /></Box>;
  if (!student) return <Typography color="error">Erreur de chargement.</Typography>;

  // « etat » : active (en cours), terminee (exclusion temporaire finie) ou levee.
  const etatDe = (s) => s.etat || (s.active ? 'active' : 'levee');
  const activeSanctions = student.sanctions?.filter((s) => etatDe(s) === 'active') || [];
  const dateFr = (iso) => (iso ? new Date(`${String(iso).slice(0, 10)}T00:00:00`).toLocaleDateString('fr-FR') : '-');
  const exclusionEnCours = activeSanctions.find((s) => s.type_sanction === 'Exclusion temporaire' && s.date_fin);

  return (
    <Box>
      <Typography variant="h5" fontWeight="bold" color="primary" gutterBottom>État Disciplinaire</Typography>
      
      {activeSanctions.length > 0 ? (
        <Alert severity="warning" sx={{ mb: 4, borderRadius: 3 }}>
          Vous avez {activeSanctions.length} sanction(s) en cours au dossier.
          {exclusionEnCours && (
            <> Vous êtes exclu(e) jusqu&apos;au <strong>{dateFr(exclusionEnCours.date_fin)}</strong> inclus.</>
          )}
        </Alert>
      ) : (
        <Alert severity="success" sx={{ mb: 4, borderRadius: 3 }}>
          Aucune sanction en cours à votre dossier.
        </Alert>
      )}

      <Card sx={{ borderRadius: 4, mb: { xs: 3, md: 4 }, boxShadow: '0 4px 20px rgba(0,0,0,0.05)' }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
            <GavelIcon color="primary" />
            <Typography variant="h6" fontWeight="bold">Historique des Sanctions</Typography>
          </Box>
          <Divider sx={{ mb: 3 }} />
          
          <TableContainer component={Box}>
            <Table sx={{ minWidth: 650 }}>
              <TableHead sx={{ bgcolor: '#F5F7FA' }}>
                <TableRow>
                  <TableCell sx={{ fontWeight: 'bold' }}>Date</TableCell>
                  <TableCell sx={{ fontWeight: 'bold' }}>Type</TableCell>
                  <TableCell sx={{ fontWeight: 'bold' }}>Motif</TableCell>
                  <TableCell sx={{ fontWeight: 'bold' }}>Durée</TableCell>
                  <TableCell align="center" sx={{ fontWeight: 'bold' }}>Statut</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {student.sanctions?.length > 0 ? (
                  student.sanctions.map((sanction) => (
                    <TableRow key={sanction.id} hover>
                      <TableCell sx={{ whiteSpace: 'nowrap' }}>{dateFr(sanction.date_sanction)}</TableCell>
                      <TableCell>
                        <Typography variant="body2" fontWeight="bold">{sanction.type_sanction}</Typography>
                      </TableCell>
                      <TableCell sx={{ maxWidth: 300 }}>
                        {sanction.motif}
                        {etatDe(sanction) === 'levee' && sanction.motif_levee && (
                          <Typography variant="caption" color="success.main" display="block">
                            Levée le {dateFr(sanction.date_levee)} : {sanction.motif_levee}
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell sx={{ whiteSpace: 'nowrap' }}>
                        {sanction.date_fin ? `Jusqu'au ${dateFr(sanction.date_fin)}` : sanction.duree || '-'}
                      </TableCell>
                      <TableCell align="center">
                        <Chip
                          label={{ active: 'En cours', terminee: 'Terminée', levee: 'Levée' }[etatDe(sanction)]}
                          size="small"
                          color={{ active: 'error', terminee: 'default', levee: 'success' }[etatDe(sanction)]}
                          variant={etatDe(sanction) === 'active' ? 'filled' : 'outlined'}
                        />
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={5} align="center" sx={{ py: 3 }}>
                      <Typography variant="body2" color="text.secondary">Aucune sanction enregistrée.</Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      <Typography variant="caption" color="text.secondary">
        Note : Les sanctions disciplinaires peuvent affecter l'obtention de certains certificats ou la participation à des activités du campus.
      </Typography>
    </Box>
  );
}
