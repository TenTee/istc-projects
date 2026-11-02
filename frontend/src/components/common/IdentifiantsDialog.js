'use client';

/**
 * Fenêtre « Identifiants de connexion » affichée après la création d'un compte ou la
 * réinitialisation d'un mot de passe. Le message prêt à envoyer peut être copié,
 * modifié, puis transmis par WhatsApp ou par e-mail.
 *
 * identifiants : { username, password, nom, email, telephone } (réponse des API).
 * Le mot de passe n'est renvoyé qu'une fois par le serveur : il faut le transmettre maintenant.
 */
import React from 'react';
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  InputAdornment,
  Stack,
  TextField,
  Tooltip,
  Typography,
  useMediaQuery,
  useTheme,
} from '@mui/material';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import CheckIcon from '@mui/icons-material/Check';
import WhatsAppIcon from '@mui/icons-material/WhatsApp';
import EmailOutlinedIcon from '@mui/icons-material/EmailOutlined';
import KeyIcon from '@mui/icons-material/Key';
import { ConfigContext } from '../../theme/ThemeRegistry';

export async function copierTexte(texte) {
  try {
    if (navigator?.clipboard?.writeText && window.isSecureContext) {
      await navigator.clipboard.writeText(texte);
      return true;
    }
  } catch {
    /* repli ci-dessous */
  }
  // Repli pour les pages servies en HTTP (adresse IP) où l'API presse-papiers est bloquée.
  try {
    const zone = document.createElement('textarea');
    zone.value = texte;
    zone.setAttribute('readonly', '');
    zone.style.position = 'fixed';
    zone.style.opacity = '0';
    document.body.appendChild(zone);
    zone.select();
    const ok = document.execCommand('copy');
    document.body.removeChild(zone);
    return ok;
  } catch {
    return false;
  }
}

/** Numéro au format international pour wa.me (chiffres seuls), sinon null. */
function numeroWhatsApp(telephone) {
  const brut = String(telephone || '').trim();
  if (!brut) return null;
  const chiffres = brut.replace(/\D/g, '');
  if (brut.startsWith('+')) return chiffres || null;
  if (brut.startsWith('00')) return chiffres.slice(2) || null;
  return null; // numéro local : on laisse choisir le destinataire dans WhatsApp
}

export function construireMessage({ identifiants, motif, etablissement, adresse }) {
  const prenomNom = identifiants?.nom ? ` ${identifiants.nom}` : '';
  const intro =
    motif === 'reinitialisation'
      ? `Votre mot de passe ${etablissement} a été réinitialisé.`
      : `Votre compte ${etablissement} a été créé.`;
  return [
    `Bonjour${prenomNom},`,
    '',
    intro,
    '',
    `Adresse : ${adresse}`,
    `Nom d'utilisateur : ${identifiants?.username || ''}`,
    `Mot de passe : ${identifiants?.password || ''}`,
    '',
    'À la première connexion, changez votre mot de passe dans « Mon profil » (menu en haut à droite).',
    'Ne communiquez ces identifiants à personne.',
  ].join('\n');
}

function ChampCopiable({ label, valeur, mono = false }) {
  const [copie, setCopie] = React.useState(false);
  const copier = async () => {
    if (await copierTexte(valeur || '')) {
      setCopie(true);
      setTimeout(() => setCopie(false), 1500);
    }
  };
  return (
    <TextField
      label={label}
      value={valeur || ''}
      fullWidth
      size="small"
      InputProps={{
        readOnly: true,
        sx: mono ? { fontFamily: 'monospace', fontWeight: 600 } : undefined,
        endAdornment: (
          <InputAdornment position="end">
            <Tooltip title={copie ? 'Copié' : 'Copier'}>
              <IconButton onClick={copier} edge="end" aria-label={`Copier ${label.toLowerCase()}`} size="small">
                {copie ? <CheckIcon color="success" fontSize="small" /> : <ContentCopyIcon fontSize="small" />}
              </IconButton>
            </Tooltip>
          </InputAdornment>
        ),
      }}
    />
  );
}

export default function IdentifiantsDialog({ open, onClose, identifiants, motif = 'creation', titre }) {
  const theme = useTheme();
  const fullScreen = useMediaQuery(theme.breakpoints.down('sm'));
  const config = React.useContext(ConfigContext);
  const etablissement = config?.nom || 'SmartCampus';
  const [message, setMessage] = React.useState('');
  const [copie, setCopie] = React.useState(false);

  // Le message est régénéré à chaque ouverture (il reste modifiable ensuite).
  React.useEffect(() => {
    if (!open || !identifiants) return undefined;
    const adresse = typeof window !== 'undefined' ? `${window.location.origin}/login` : '';
    const timer = setTimeout(() => {
      setMessage(construireMessage({ identifiants, motif, etablissement, adresse }));
      setCopie(false);
    }, 0);
    return () => clearTimeout(timer);
  }, [open, identifiants, motif, etablissement]);

  if (!identifiants) return null;

  const copierMessage = async () => {
    if (await copierTexte(message)) {
      setCopie(true);
      setTimeout(() => setCopie(false), 2000);
    }
  };

  const numero = numeroWhatsApp(identifiants.telephone);
  const lienWhatsApp = `https://wa.me/${numero || ''}?text=${encodeURIComponent(message)}`;
  const sujet = motif === 'reinitialisation' ? `${etablissement} : nouveau mot de passe` : `${etablissement} : vos identifiants`;
  const lienEmail = `mailto:${identifiants.email || ''}?subject=${encodeURIComponent(sujet)}&body=${encodeURIComponent(message)}`;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth fullScreen={fullScreen} scroll="paper">
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <KeyIcon color="primary" />
        {titre || (motif === 'reinitialisation' ? 'Mot de passe réinitialisé' : 'Compte créé')}
      </DialogTitle>
      <DialogContent dividers>
        <Alert severity="warning" sx={{ mb: 2 }}>
          Transmettez ces identifiants maintenant : le mot de passe ne sera plus affiché après fermeture de cette fenêtre.
        </Alert>
        {identifiants.nom && (
          <Typography variant="subtitle2" sx={{ mb: 1.5 }}>
            {identifiants.nom}
          </Typography>
        )}
        <Stack spacing={1.5} sx={{ mb: 2 }}>
          <ChampCopiable label="Nom d'utilisateur" valeur={identifiants.username} mono />
          <ChampCopiable label="Mot de passe" valeur={identifiants.password} mono />
        </Stack>
        <TextField
          label="Message à envoyer"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          fullWidth
          multiline
          minRows={8}
          helperText="Vous pouvez modifier le message avant de l'envoyer."
        />
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 2 }}>
          <Button
            variant="contained"
            startIcon={copie ? <CheckIcon /> : <ContentCopyIcon />}
            onClick={copierMessage}
            color={copie ? 'success' : 'primary'}
          >
            {copie ? 'Message copié' : 'Copier le message'}
          </Button>
          <Button
            variant="outlined"
            startIcon={<WhatsAppIcon />}
            component="a"
            href={lienWhatsApp}
            target="_blank"
            rel="noopener noreferrer"
            sx={{ color: '#128C7E', borderColor: '#25D366' }}
          >
            WhatsApp
          </Button>
          <Button variant="outlined" startIcon={<EmailOutlinedIcon />} component="a" href={lienEmail}>
            E-mail
          </Button>
        </Box>
        {!numero && identifiants.telephone && (
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
            Numéro {identifiants.telephone} sans indicatif pays : choisissez le destinataire dans WhatsApp.
          </Typography>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Fermer</Button>
      </DialogActions>
    </Dialog>
  );
}
