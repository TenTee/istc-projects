'use client';

/**
 * Correction ou suppression d'un paiement (droit Finance en écriture).
 * Le motif est obligatoire : il est conservé dans le journal des paiements avec les valeurs
 * avant / après. Soldes et échéancier de l'étudiant sont recalculés par le serveur.
 */
import React from 'react';
import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid,
  MenuItem,
  TextField,
  Typography,
  useMediaQuery,
  useTheme,
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import DeleteForeverIcon from '@mui/icons-material/DeleteForever';
import { paiementsService } from '../../services/api/services';
import { getApiErrorMessage } from '../../services/api/client';

export const MOYENS_PAIEMENT = [
  { value: 'cash', label: 'Espèces' },
  { value: 'mobile_money', label: 'Mobile Money' },
  { value: 'orange_money', label: 'Orange Money' },
  { value: 'virement', label: 'Virement bancaire' },
  { value: 'cheque', label: 'Chèque' },
];

const MOTIF_MIN = 5;

function versChampDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function formatFCFA(val) {
  return `${Number(val || 0).toLocaleString('fr-FR')} FCFA`;
}

function premiereErreur(valeur) {
  if (!valeur) return '';
  return Array.isArray(valeur) ? valeur.join(' ') : String(valeur);
}

export default function CorrectionPaiementDialog({ open, mode = 'modifier', paiement, onClose, onDone }) {
  const theme = useTheme();
  const fullScreen = useMediaQuery(theme.breakpoints.down('sm'));
  const suppression = mode === 'supprimer';
  const [form, setForm] = React.useState({});
  const [motif, setMotif] = React.useState('');
  const [erreurs, setErreurs] = React.useState({});
  const [envoi, setEnvoi] = React.useState(false);

  React.useEffect(() => {
    if (!open || !paiement) return undefined;
    const timer = setTimeout(() => {
      setForm({
        montant_paye: String(Number(paiement.montant_paye || 0)),
        paiement_type: paiement.paiement_type || 'FORMATION',
        moyen_paiement: paiement.moyen_paiement || 'cash',
        date_paiement: versChampDate(paiement.date_paiement),
      });
      setMotif('');
      setErreurs({});
    }, 0);
    return () => clearTimeout(timer);
  }, [open, paiement]);

  if (!paiement) return null;

  const changer = (champ) => (e) => setForm((f) => ({ ...f, [champ]: e.target.value }));

  const valider = async () => {
    const locales = {};
    if (motif.trim().length < MOTIF_MIN) locales.motif = `Indiquez le motif (au moins ${MOTIF_MIN} caractères).`;
    if (!suppression) {
      if (!(Number(form.montant_paye) > 0)) locales.montant_paye = 'Le montant doit être supérieur à 0.';
      if (!form.date_paiement) locales.date_paiement = 'Date requise.';
      else if (new Date(form.date_paiement) > new Date()) locales.date_paiement = 'La date ne peut pas être dans le futur.';
    }
    setErreurs(locales);
    if (Object.keys(locales).length) return;

    setEnvoi(true);
    try {
      if (suppression) {
        await paiementsService.supprimer(paiement.id, motif.trim());
      } else {
        await paiementsService.corriger(
          paiement.id,
          {
            montant_paye: form.montant_paye,
            paiement_type: form.paiement_type,
            moyen_paiement: form.moyen_paiement,
            date_paiement: new Date(form.date_paiement).toISOString(),
          },
          motif.trim(),
        );
      }
      onDone?.(suppression ? 'Paiement supprimé. Les soldes ont été recalculés.' : 'Paiement corrigé. Les soldes ont été recalculés.');
    } catch (error) {
      const data = error?.response?.data;
      const champs = data && typeof data === 'object' && !Array.isArray(data) ? data : {};
      const connus = ['montant_paye', 'paiement_type', 'moyen_paiement', 'date_paiement', 'motif'];
      const trouves = Object.fromEntries(connus.filter((c) => champs[c]).map((c) => [c, premiereErreur(champs[c])]));
      setErreurs({
        ...trouves,
        general: Object.keys(trouves).length ? '' : getApiErrorMessage(error, 'Opération impossible.'),
      });
    } finally {
      setEnvoi(false);
    }
  };

  const titre = suppression ? 'Supprimer le paiement' : 'Corriger le paiement';

  return (
    <Dialog open={open} onClose={envoi ? undefined : onClose} maxWidth="sm" fullWidth fullScreen={fullScreen}>
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1, color: suppression ? 'error.main' : 'primary.main' }}>
        {suppression ? <DeleteForeverIcon /> : <EditIcon />}
        {titre}
      </DialogTitle>
      <DialogContent dividers>
        <Typography variant="body2" sx={{ mb: 2 }}>
          Reçu <strong>{paiement.numero_recu || `n° ${paiement.id}`}</strong>
          {paiement.etudiant_nom ? <> · {paiement.etudiant_nom}</> : null} ·{' '}
          <strong>{formatFCFA(paiement.montant_paye)}</strong>
          {paiement.date_paiement ? <> du {new Date(paiement.date_paiement).toLocaleDateString('fr-FR')}</> : null}
        </Typography>

        {erreurs.general && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {erreurs.general}
          </Alert>
        )}

        {suppression ? (
          <Alert severity="warning" sx={{ mb: 2 }}>
            Le paiement sera définitivement retiré des soldes et de l&apos;échéancier de l&apos;étudiant. Son reçu ne sera
            plus valable. L&apos;opération reste visible dans le journal des paiements.
          </Alert>
        ) : (
          <Grid container spacing={2} sx={{ mb: 1 }}>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Montant payé (FCFA)"
                type="number"
                value={form.montant_paye || ''}
                onChange={changer('montant_paye')}
                error={Boolean(erreurs.montant_paye)}
                helperText={erreurs.montant_paye}
                inputProps={{ min: 1 }}
                fullWidth
                size="small"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                select
                label="Type"
                value={form.paiement_type || 'FORMATION'}
                onChange={changer('paiement_type')}
                error={Boolean(erreurs.paiement_type)}
                helperText={erreurs.paiement_type}
                fullWidth
                size="small"
              >
                <MenuItem value="FORMATION">Frais de formation</MenuItem>
                <MenuItem value="INSCRIPTION">Frais d&apos;inscription</MenuItem>
              </TextField>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                select
                label="Mode de paiement"
                value={form.moyen_paiement || 'cash'}
                onChange={changer('moyen_paiement')}
                fullWidth
                size="small"
              >
                {MOYENS_PAIEMENT.map((m) => (
                  <MenuItem key={m.value} value={m.value}>
                    {m.label}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Date du paiement"
                type="datetime-local"
                value={form.date_paiement || ''}
                onChange={changer('date_paiement')}
                error={Boolean(erreurs.date_paiement)}
                helperText={erreurs.date_paiement}
                InputLabelProps={{ shrink: true }}
                fullWidth
                size="small"
              />
            </Grid>
          </Grid>
        )}

        <TextField
          label={suppression ? 'Motif de la suppression' : 'Motif de la correction'}
          placeholder={suppression ? 'Ex. : saisi en double, chèque rejeté…' : 'Ex. : erreur de saisie du montant…'}
          value={motif}
          onChange={(e) => setMotif(e.target.value)}
          error={Boolean(erreurs.motif)}
          helperText={erreurs.motif || 'Obligatoire. Conservé dans le journal avec votre nom.'}
          multiline
          minRows={2}
          fullWidth
          required
          sx={{ mt: 1 }}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={envoi}>
          Annuler
        </Button>
        <Button
          onClick={valider}
          variant="contained"
          color={suppression ? 'error' : 'primary'}
          disabled={envoi}
          startIcon={suppression ? <DeleteForeverIcon /> : <EditIcon />}
        >
          {envoi ? 'Enregistrement…' : suppression ? 'Supprimer' : 'Enregistrer la correction'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
