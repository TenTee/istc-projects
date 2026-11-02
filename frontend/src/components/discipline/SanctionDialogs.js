'use client';

/**
 * Fenêtres de gestion des sanctions disciplinaires :
 * - SanctionFormDialog : enregistrer ou corriger une sanction ;
 * - LeverSanctionDialog : lever une sanction (motif obligatoire, l'historique est conservé).
 * Utilisées par la page Discipline et par la fiche de l'étudiant.
 */
import React from 'react';
import {
  Alert,
  Button,
  Chip,
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
import GavelIcon from '@mui/icons-material/Gavel';
import LockOpenIcon from '@mui/icons-material/LockOpen';
import SearchableSelect from '../common/SearchableSelect';
import { sanctionsService } from '../../services/api/services';
import { getApiErrorMessage } from '../../services/api/client';

export const TYPES_SANCTION = ['Avertissement', 'Blâme', 'Exclusion temporaire', 'Exclusion définitive'];

export const COULEURS_TYPE = {
  Avertissement: 'info',
  'Blâme': 'warning',
  'Exclusion temporaire': 'error',
  'Exclusion définitive': 'error',
};

export const ETATS = {
  active: { label: 'En cours', color: 'error' },
  terminee: { label: 'Terminée', color: 'default' },
  levee: { label: 'Levée', color: 'success' },
};

export function dateFr(iso) {
  if (!iso) return '-';
  const [a, m, j] = String(iso).slice(0, 10).split('-');
  return `${j}/${m}/${a}`;
}

export function periodeSanction(s) {
  if (s.type_sanction === 'Exclusion temporaire' && s.date_fin) {
    return `Du ${dateFr(s.date_sanction)} au ${dateFr(s.date_fin)}${s.duree ? ` (${s.duree})` : ''}`;
  }
  return s.duree || '-';
}

/** Lien WhatsApp vers le parent (wa.me) avec un message prêt à envoyer, ou null sans numéro. */
export function lienWhatsAppParent(sanction, etablissement = 'SmartCampus') {
  const brut = String(sanction?.whatsapp_parent || '').trim();
  if (!brut) return null;
  let chiffres = brut.replace(/\D/g, '');
  if (brut.startsWith('00')) chiffres = chiffres.slice(2);
  const lignes = [
    `Bonjour${sanction.nom_parent ? ` ${sanction.nom_parent}` : ''},`,
    '',
    `${etablissement} vous informe qu'une sanction disciplinaire a été prononcée à l'encontre de ${sanction.etudiant_nom} :`,
    `- ${sanction.type_sanction} du ${dateFr(sanction.date_sanction)}`,
  ];
  if (sanction.type_sanction === 'Exclusion temporaire' && sanction.date_fin) {
    lignes.push(`- Exclusion jusqu'au ${dateFr(sanction.date_fin)} inclus`);
  }
  lignes.push(`- Motif : ${sanction.motif}`, '', "Nous restons à votre disposition pour en parler.");
  return `https://wa.me/${chiffres}?text=${encodeURIComponent(lignes.join('\n'))}`;
}

function premiereErreur(v) {
  if (!v) return '';
  return Array.isArray(v) ? v.join(' ') : String(v);
}

function erreursServeur(error, champs) {
  const data = error?.response?.data;
  const obj = data && typeof data === 'object' && !Array.isArray(data) ? data : {};
  const trouves = Object.fromEntries(champs.filter((c) => obj[c]).map((c) => [c, premiereErreur(obj[c])]));
  return { ...trouves, general: Object.keys(trouves).length ? '' : getApiErrorMessage(error, 'Opération impossible.') };
}

const aujourdhui = () => {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
};

/**
 * sanction : sanction à corriger (sinon création).
 * etudiantFixe : { id, nom } pour créer depuis la fiche d'un étudiant (pas de choix d'étudiant).
 * etudiants : liste [{ id, nom, matricule }] pour choisir l'étudiant (page Discipline).
 */
export function SanctionFormDialog({ open, onClose, onSaved, sanction = null, etudiantFixe = null, etudiants = [] }) {
  const theme = useTheme();
  const fullScreen = useMediaQuery(theme.breakpoints.down('sm'));
  const edition = Boolean(sanction);
  const [form, setForm] = React.useState({});
  const [erreurs, setErreurs] = React.useState({});
  const [envoi, setEnvoi] = React.useState(false);

  React.useEffect(() => {
    if (!open) return undefined;
    const timer = setTimeout(() => {
      setForm(
        sanction
          ? {
              etudiant: sanction.etudiant,
              type_sanction: sanction.type_sanction,
              date_sanction: sanction.date_sanction,
              date_fin: sanction.date_fin || '',
              motif: sanction.motif,
            }
          : { etudiant: etudiantFixe?.id || '', type_sanction: 'Avertissement', date_sanction: aujourdhui(), date_fin: '', motif: '' },
      );
      setErreurs({});
    }, 0);
    return () => clearTimeout(timer);
  }, [open, sanction, etudiantFixe]);

  const changer = (champ) => (e) => setForm((f) => ({ ...f, [champ]: e.target.value }));
  const temporaire = form.type_sanction === 'Exclusion temporaire';

  const enregistrer = async () => {
    const locales = {};
    if (!form.etudiant) locales.etudiant = "Choisissez l'étudiant.";
    if (!form.date_sanction) locales.date_sanction = 'Date requise.';
    if ((form.motif || '').trim().length < 5) locales.motif = 'Décrivez le motif (au moins 5 caractères).';
    if (temporaire && !form.date_fin) locales.date_fin = "Indiquez le dernier jour de l'exclusion.";
    if (temporaire && form.date_fin && form.date_fin < form.date_sanction) locales.date_fin = 'La fin doit être après le début.';
    setErreurs(locales);
    if (Object.keys(locales).length) return;

    const payload = {
      type_sanction: form.type_sanction,
      date_sanction: form.date_sanction,
      date_fin: temporaire ? form.date_fin : null,
      motif: form.motif.trim(),
    };
    setEnvoi(true);
    try {
      const resultat = edition
        ? await sanctionsService.update(sanction.id, payload)
        : await sanctionsService.create({ ...payload, etudiant: form.etudiant });
      onSaved?.(resultat, edition);
    } catch (error) {
      setErreurs(erreursServeur(error, ['etudiant', 'type_sanction', 'date_sanction', 'date_fin', 'motif']));
    } finally {
      setEnvoi(false);
    }
  };

  const nomEtudiant = sanction?.etudiant_nom || etudiantFixe?.nom;

  return (
    <Dialog open={open} onClose={envoi ? undefined : onClose} maxWidth="sm" fullWidth fullScreen={fullScreen}>
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1, color: 'primary.main' }}>
        <GavelIcon />
        {edition ? 'Corriger la sanction' : 'Nouvelle sanction'}
      </DialogTitle>
      <DialogContent dividers>
        {erreurs.general && <Alert severity="error" sx={{ mb: 2 }}>{erreurs.general}</Alert>}
        <Grid container spacing={2}>
          <Grid item xs={12}>
            {nomEtudiant ? (
              <Typography variant="subtitle1" fontWeight="bold">
                {nomEtudiant}
              </Typography>
            ) : (
              <SearchableSelect
                label="Étudiant"
                required
                options={etudiants}
                value={form.etudiant || ''}
                onChange={(v) => setForm((f) => ({ ...f, etudiant: v }))}
                getOptionLabel={(e) => (e ? `${e.nom}${e.matricule ? ` (${e.matricule})` : ''}` : '')}
                getOptionValue={(e) => (e ? e.id : '')}
                placeholder="Nom ou matricule…"
                error={Boolean(erreurs.etudiant)}
                helperText={erreurs.etudiant}
              />
            )}
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField select label="Type de sanction" value={form.type_sanction || 'Avertissement'} onChange={changer('type_sanction')}
              error={Boolean(erreurs.type_sanction)} helperText={erreurs.type_sanction} fullWidth size="small">
              {TYPES_SANCTION.map((t) => (
                <MenuItem key={t} value={t}>{t}</MenuItem>
              ))}
            </TextField>
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField label={temporaire ? "Début de l'exclusion" : 'Date de la sanction'} type="date" value={form.date_sanction || ''}
              onChange={changer('date_sanction')} error={Boolean(erreurs.date_sanction)} helperText={erreurs.date_sanction}
              InputLabelProps={{ shrink: true }} inputProps={{ max: aujourdhui() }} fullWidth size="small" />
          </Grid>
          {temporaire && (
            <Grid item xs={12} sm={6}>
              <TextField label="Dernier jour d'exclusion" type="date" value={form.date_fin || ''} onChange={changer('date_fin')}
                error={Boolean(erreurs.date_fin)} helperText={erreurs.date_fin || 'Inclus. La durée est calculée.'}
                InputLabelProps={{ shrink: true }} inputProps={{ min: form.date_sanction || undefined }} fullWidth size="small" />
            </Grid>
          )}
          <Grid item xs={12}>
            <TextField label="Motif" value={form.motif || ''} onChange={changer('motif')} error={Boolean(erreurs.motif)}
              helperText={erreurs.motif || 'Faits reprochés, visible par l’étudiant dans son portail.'}
              multiline minRows={3} fullWidth required />
          </Grid>
        </Grid>
        {form.type_sanction === 'Exclusion définitive' && (
          <Alert severity="warning" sx={{ mt: 2 }}>
            L&apos;exclusion définitive est inscrite au dossier mais ne ferme pas le compte de l&apos;étudiant : désactivez-le
            ou supprimez l&apos;étudiant si nécessaire.
          </Alert>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={envoi}>Annuler</Button>
        <Button variant="contained" onClick={enregistrer} disabled={envoi} startIcon={<GavelIcon />}>
          {envoi ? 'Enregistrement…' : 'Enregistrer'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

export function LeverSanctionDialog({ open, onClose, onDone, sanction }) {
  const theme = useTheme();
  const fullScreen = useMediaQuery(theme.breakpoints.down('sm'));
  const [motif, setMotif] = React.useState('');
  const [erreurs, setErreurs] = React.useState({});
  const [envoi, setEnvoi] = React.useState(false);

  React.useEffect(() => {
    if (!open) return undefined;
    const timer = setTimeout(() => {
      setMotif('');
      setErreurs({});
    }, 0);
    return () => clearTimeout(timer);
  }, [open]);

  if (!sanction) return null;

  const lever = async () => {
    if (motif.trim().length < 5) {
      setErreurs({ motif_levee: 'Indiquez le motif de la levée (au moins 5 caractères).' });
      return;
    }
    setEnvoi(true);
    try {
      const resultat = await sanctionsService.lever(sanction.id, motif.trim());
      onDone?.(resultat);
    } catch (error) {
      setErreurs(erreursServeur(error, ['motif_levee']));
    } finally {
      setEnvoi(false);
    }
  };

  return (
    <Dialog open={open} onClose={envoi ? undefined : onClose} maxWidth="sm" fullWidth fullScreen={fullScreen}>
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1, color: 'success.main' }}>
        <LockOpenIcon />
        Lever la sanction
      </DialogTitle>
      <DialogContent dividers>
        <Typography variant="body2" sx={{ mb: 2 }}>
          <Chip size="small" label={sanction.type_sanction} color={COULEURS_TYPE[sanction.type_sanction] || 'default'} sx={{ mr: 1 }} />
          <strong>{sanction.etudiant_nom}</strong> · {dateFr(sanction.date_sanction)}
        </Typography>
        {erreurs.general && <Alert severity="error" sx={{ mb: 2 }}>{erreurs.general}</Alert>}
        <Alert severity="info" sx={{ mb: 2 }}>
          La sanction ne compte plus comme « en cours » mais reste dans l&apos;historique, avec la date, le motif de la levée
          et votre nom.
        </Alert>
        <TextField label="Motif de la levée" value={motif} onChange={(e) => setMotif(e.target.value)}
          error={Boolean(erreurs.motif_levee)} helperText={erreurs.motif_levee || 'Ex. : bon comportement, décision du conseil…'}
          multiline minRows={2} fullWidth required />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={envoi}>Annuler</Button>
        <Button variant="contained" color="success" onClick={lever} disabled={envoi} startIcon={<LockOpenIcon />}>
          {envoi ? 'Enregistrement…' : 'Lever la sanction'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
