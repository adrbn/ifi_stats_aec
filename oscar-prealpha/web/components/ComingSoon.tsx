import { Panel } from "./Card";
import { PageTitle } from "./PageTitle";
import { Alert } from "./Alert";

export function ComingSoon({
  group,
  title,
  note,
}: {
  group: string;
  title: string;
  note: string;
}) {
  return (
    <div className="space-y-5">
      <PageTitle eyebrow={group} title={title} />
      <Panel>
        <Alert variant="info" title="Vue en cours de portage">
          {note} Le calcul existe déjà dans le moteur OSCAR (fonctions pandas réutilisées) ; cette vue
          sera branchée sur l'API dans la prochaine itération de la pre-alpha.
        </Alert>
      </Panel>
    </div>
  );
}
