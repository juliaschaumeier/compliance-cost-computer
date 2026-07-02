import HeaderHelpPopover from "@/components/HeaderHelpPopover";
import ModelSelector from "@/components/ModelSelector";
import SessionMenu from "@/components/SessionMenu";

export default function Header() {
  return (
    <header className="border-b border-white/20 bg-gradient-to-r from-slate-900 via-slate-800 to-slate-700 text-white shadow-xl">
      <div className="mx-auto flex min-h-20 max-w-7xl items-center justify-between gap-6 px-4 py-3 sm:px-6 lg:px-8">
        <div className="flex items-center gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white/10 text-2xl font-bold shadow-inner">
            CCC
          </div>
          <div>
            <h1 className="text-xl font-semibold tracking-tight sm:text-2xl">
              Compliance-Cost Computer
            </h1>
            <p className="text-xs text-slate-200/80 sm:text-sm">
              Errechnet den jährlichen Erfüllungsaufwand einer Gesetzesänderung.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <SessionMenu variant="header" />
          <ModelSelector />
          <HeaderHelpPopover />
        </div>
      </div>
    </header>
  );
}
