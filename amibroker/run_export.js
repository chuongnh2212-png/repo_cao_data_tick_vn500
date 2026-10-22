// run_export.js - Mo AmiBroker, chay Analysis project (.apx) cua vnflow_export.afl, cho xong roi thoat.
// Chay: cscript //nologo amibroker\run_export.js "C:\vnflow\vnflow_export.apx"
// File .apx tao 1 lan trong AmiBroker: Analysis > Formula vnflow_export.afl > Apply to watchlist VN500
//   > Range: "N last days" = 10 > File > Save As... vnflow_export.apx
var apx = WScript.Arguments.length > 0 ? WScript.Arguments(0) : "C:\\vnflow\\vnflow_export.apx";
var fso = new ActiveXObject("Scripting.FileSystemObject");
if (!fso.FileExists(apx)) { WScript.Echo("Khong thay file project: " + apx); WScript.Quit(2); }
var AB = new ActiveXObject("Broker.Application");
var AA = AB.AnalysisDocs.Open(apx);
if (!AA) { WScript.Echo("Khong mo duoc project " + apx); WScript.Quit(3); }
AA.Run(1);                       // 1 = Exploration
var waited = 0;
while (AA.IsBusy && waited < 1800) { WScript.Sleep(1000); waited++; }
AA.Close();
WScript.Echo(waited >= 1800 ? "Qua thoi gian cho (30 phut)" : "Xuat xong sau " + waited + " giay");
WScript.Quit(waited >= 1800 ? 4 : 0);
