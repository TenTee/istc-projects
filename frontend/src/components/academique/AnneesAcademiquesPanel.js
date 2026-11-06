'use client';

/**
 * Gestion des années académiques : liste, création, modification, activation, suppression.
 * Les actions demandent le droit « Gérer les années académiques » du rôle (vérifié aussi par
 * le serveur). Une seule année est active : en activer une archive la précédente.
 * Utilisé par la page « Années académiques » et par l'onglet de « Structure Académique ».
 */
import React from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  Grid,
  IconButton,
  Paper,
  Snackbar,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
  useMediaQuery,
  useTheme,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import PlayCircleOutlineIcon from '@mui/icons-material/PlayCircleOutline';
import { anneesAcademiquesService } from '../../services/api/services';
import { getApiErrorMessage } from '../../services/api/client';
import { useUserPermissions } from '../../utils/permissions';
import { useAcademicYear } from '../../context/AcademicYearContext';

const toList = (data) => (Array.isArray(data) ? data : data?.results || []);

function dateFr(iso) {
  if (!iso) return '-';
  const [a, m, j] = String(iso).slice(0, 10).split('-');
  return `${j}/${m}/${a}`;
}

const VIDE = { libelle: '', description: '', date_debut: '', date_fin: '', activer: false };

export default function AnneesAcademiquesPanel() {
  const theme = useTheme();
  const fullScreen = useMediaQuery(theme.breakpoints.down('sm'));
  const { canWrite } = useUserPermissions();
  const peutGerer = canWrite('can_manage_annees');
  const { refreshYears } = useAcademicYear();

  const [annees, setAnnees] = React.useState([]);
  const [chargement, setChargement] = React.useState(true);
  const [formulaire, setFormulaire] = React.useState({ open: false, annee: null });
  const [form, setForm] = React.useState(VIDE);
  const [erreurs, setErreurs] = React.useState({});
  const [envoi, setEnvoi] = React.useState(false);
  const [aActiver, setAActiver] = React.useState(null);
  const [toast, setToast] = React.useState({ open: false, message: '', severity: 'success' });

  const notifier = (message, severity = 'success') => setToast({ open: true, message, severity });

  const charger = React.useCallback(async () => {
    setChargement(true);
    try {
      setAnnees(toList(await anneesAcademiquesService.list()));
    } catch (e) {
      notifier(getApiErrorMessage(e, 'Chargement des années impossible.'), 'error');
    } finally {
      setChargement(false);
    }
  }, []);

  React.useEffect(() => {
    const timer = setTimeout(charger, 0);
    return () => clearTimeout(timer);
  }, [charger]);

  const apresChangement = async (message) => {
    notifier(message);
    await charger();
    // Le sélecteur d'année de l'en-tête suit les changements (nouvelle année active, etc.).
    refreshYears?.();
  };

  const ouvrir = (annee = null) => {
    setForm(
      annee
        ? { libelle: annee.libelle, description: annee.description || '', date_debut: annee.date_debut || '', date_fin: annee.date_fin || '', activer: false }
        : VIDE,
    );
    setErreurs({});
    setFormulaire({ open: true, annee });
  };

  const enregistrer = async () => {
    const locales = {};
    if (!form.libelle.trim()) locales.libelle = 'Libellé requis (ex. 2027-2028).';
    if (form.date_debut && form.date_fin && form.date_fin <= form.date_debut) locales.date_fin = 'La fin doit être après le début.';
    setErreurs(locales);
    if (Object.keys(locales).length) return;
    const payload = {
      libelle: form.libelle.trim(),
      description: form.description,
      date_debut: form.date_debut || null,
      date_fin: form.date_fin || null,
    };
    setEnvoi(true);
    try {
      if (formulaire.annee) {
        await anneesAcademiquesService.patch(formulaire.annee.id, payload);
        setFormulaire({ open: false, annee: null });
        await apresChangement('Année modifiée.');
      } else {
        const creee = await anneesAcademiquesService.create(payload);
        if (form.activer && creee?.id) await anneesAcademiquesService.activer(creee.id);
        setFormulaire({ open: false, annee: null });
        await apresChangement(form.activer ? `Année ${payload.libelle} créée et activée.` : `Année ${payload.libelle} créée.`);
      }
    } catch (e) {
      const data = e?.response?.data || {};
      const champ = (c) => (Array.isArray(data[c]) ? data[c].join(' ') : data[c]);
      setErreurs({
        libelle: champ('libelle'),
        date_fin: champ('date_fin'),
        general: champ('libelle') || champ('date_fin') ? '' : getApiErrorMessage(e, 'Enregistrement impossible.'),
      });
    } finally {
      setEnvoi(false);
    }
  };

  const activer = async () => {
    try {
      await anneesAcademiquesService.activer(aActiver.id);
      const libelle = aActiver.libelle;
      setAActiver(null);
      await apresChangement(`L'année ${libelle} est maintenant l'année active.`);
    } catch (e) {
      setAActiver(null);
      notifier(getApiErrorMessage(e, 'Activation impossible.'), 'error');
    }
  };

  const supprimer = async (annee) => {
    if (!window.confirm(`Supprimer l'année ${annee.libelle} ? Seule une année sans données peut être supprimée.`)) return;
    try {
      await anneesAcademiquesService.remove(annee.id);
      await apresChangement('Année supprimée.');
    } catch (e) {
      notifier(getApiErrorMessage(e, 'Suppression impossible.'), 'error');
    }
  };

  const active = annees.find((a) => a.est_active);

  return (
    <Box>
      <Box sx={{ display: 'flex', flexDirection: { xs: 'column', sm: 'row' }, justifyContent: 'space-between', alignItems: { xs: 'stretch', sm: 'center' }, gap: 2, mb: 2 }}>
        <Typography variant="body2" color="text.secondary">
          Une seule année est active à la fois. Les autres sont <strong>archivées</strong> : leur accès dépend du droit
          « Années archivées » de chaque rôle.
        </Typography>
        {peutGerer && (
          <Button variant="contained" startIcon={<AddIcon />} onClick={() => ouvrir()} sx={{ flexShrink: 0 }}>
            Nouvelle année
          </Button>
        )}
      </Box>

      <TableContainer component={Paper} sx={{ borderRadius: 3 }}>
        <Table sx={{ minWidth: 560 }}>
          <TableHead sx={{ bgcolor: '#F5F7FA' }}>
            <TableRow>
              <TableCell sx={{ fontWeight: 'bold' }}>Libellé</TableCell>
              <TableCell sx={{ fontWeight: 'bold' }}>Début</TableCell>
              <TableCell sx={{ fontWeight: 'bold' }}>Fin</TableCell>
              <TableCell sx={{ fontWeight: 'bold' }}>Statut</TableCell>
              {peutGerer && <TableCell align="right" sx={{ fontWeight: 'bold' }}>Actions</TableCell>}
            </TableRow>
          </TableHead>
          <TableBody>
            {chargement ? (
              <TableRow><TableCell colSpan={5} align="center" sx={{ py: 4 }}><CircularProgress size={24} /></TableCell></TableRow>
            ) : annees.length === 0 ? (
              <TableRow><TableCell colSpan={5} align="center" sx={{ py: 4 }}>Aucune année académique.</TableCell></TableRow>
            ) : (
              annees.map((a) => (
                <TableRow key={a.id} hover>
                  <TableCell sx={{ fontWeight: 600 }}>
                    {a.libelle}
                    {a.description ? <Typography variant="caption" color="text.secondary" display="block">{a.description}</Typography> : null}
                  </TableCell>
                  <TableCell>{dateFr(a.date_debut)}</TableCell>
                  <TableCell>{dateFr(a.date_fin)}</TableCell>
                  <TableCell>
                    <Chip size="small" label={a.est_active ? 'Active' : 'Archivée'} color={a.est_active ? 'success' : 'default'} variant={a.est_active ? 'filled' : 'outlined'} />
                  </TableCell>
                  {peutGerer && (
                    <TableCell align="right" sx={{ whiteSpace: 'nowrap' }}>
                      {!a.est_active && (
                        <Tooltip title="Faire de cette année l'année active">
                          <Button size="small" startIcon={<PlayCircleOutlineIcon />} onClick={() => setAActiver(a)} sx={{ mr: 1 }}>
                            Activer
                          </Button>
                        </Tooltip>
                      )}
                      <Tooltip title="Modifier">
                        <IconButton size="small" color="primary" onClick={() => ouvrir(a)} aria-label={`Modifier l'année ${a.libelle}`}>
                          <EditIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      {!a.est_active && (
                        <Tooltip title="Supprimer (année sans données uniquement)">
                          <IconButton size="small" color="error" onClick={() => supprimer(a)} aria-label={`Supprimer l'année ${a.libelle}`}>
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      )}
                    </TableCell>
                  )}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={formulaire.open} onClose={() => !envoi && setFormulaire({ open: false, annee: null })} maxWidth="sm" fullWidth fullScreen={fullScreen}>
        <DialogTitle>{formulaire.annee ? `Modifier l'année ${formulaire.annee.libelle}` : 'Nouvelle année académique'}</DialogTitle>
        <DialogContent dividers>
          {erreurs.general && <Alert severity="error" sx={{ mb: 2 }}>{erreurs.general}</Alert>}
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <TextField label="Libellé" placeholder="2027-2028" value={form.libelle} onChange={(e) => setForm({ ...form, libelle: e.target.value })}
                error={Boolean(erreurs.libelle)} helperText={erreurs.libelle} inputProps={{ maxLength: 15 }} fullWidth required size="small" />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField label="Début" type="date" value={form.date_debut} onChange={(e) => setForm({ ...form, date_debut: e.target.value })}
                InputLabelProps={{ shrink: true }} fullWidth size="small" />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField label="Fin" type="date" value={form.date_fin} onChange={(e) => setForm({ ...form, date_fin: e.target.value })}
                error={Boolean(erreurs.date_fin)} helperText={erreurs.date_fin} InputLabelProps={{ shrink: true }} fullWidth size="small" />
            </Grid>
            <Grid item xs={12}>
              <TextField label="Description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} fullWidth multiline minRows={2} size="small" />
            </Grid>
            {!formulaire.annee && (
              <Grid item xs={12}>
                <FormControlLabel
                  control={<Switch checked={form.activer} onChange={(e) => setForm({ ...form, activer: e.target.checked })} />}
                  label="En faire l'année active maintenant"
                />
                {form.activer && (
                  <Alert severity="warning" sx={{ mt: 1 }}>
                    L&apos;année active actuelle{active ? ` (${active.libelle})` : ''} sera archivée.
                  </Alert>
                )}
              </Grid>
            )}
          </Grid>
          {!formulaire.annee && (
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 2 }}>
              Les classes de l&apos;année précédente sont recopiées automatiquement dans la nouvelle année.
            </Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setFormulaire({ open: false, annee: null })} disabled={envoi}>Annuler</Button>
          <Button variant="contained" onClick={enregistrer} disabled={envoi}>{envoi ? 'Enregistrement…' : 'Enregistrer'}</Button>
        </DialogActions>
      </Dialog>

      <Dialog open={Boolean(aActiver)} onClose={() => setAActiver(null)} maxWidth="xs" fullWidth>
        <DialogTitle>Activer l&apos;année {aActiver?.libelle} ?</DialogTitle>
        <DialogContent>
          <Typography variant="body2" sx={{ mb: 2 }}>
            Elle devient l&apos;année de travail de toute la plateforme.
          </Typography>
          <Alert severity="warning">
            L&apos;année active actuelle{active ? ` (${active.libelle})` : ''} sera archivée : seuls les rôles ayant le droit
            « Années archivées » pourront encore y accéder.
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAActiver(null)}>Annuler</Button>
          <Button variant="contained" onClick={activer} startIcon={<PlayCircleOutlineIcon />}>Activer</Button>
        </DialogActions>
      </Dialog>

      <Snackbar open={toast.open} autoHideDuration={5000} onClose={() => setToast((t) => ({ ...t, open: false }))}>
        <Alert severity={toast.severity} onClose={() => setToast((t) => ({ ...t, open: false }))}>{toast.message}</Alert>
      </Snackbar>
    </Box>
  );
}
