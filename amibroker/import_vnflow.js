// import_vnflow.js - nap amibroker_out\vnflow_daily.csv vao CSDL AmiBroker dang mo.
// Chay: cscript //nologo amibroker\import_vnflow.js [duong_dan_file_csv]
// Yeu cau: file vnflow.format da duoc chep vao thu muc AmiBroker\Formats.
var fso = new ActiveXObject("Scripting.FileSystemObject");
var here = fso.GetParentFolderName(WScript.ScriptFullName);
var file = WScript.Arguments.length > 0 ? WScript.Arguments(0)
         : fso.BuildPath(fso.GetParentFolderName(here), "amibroker_out\\vnflow_daily.csv");
if (!fso.FileExists(file)) { WScript.Echo("Khong thay file: " + file); WScript.Quit(1); }
var AB = new ActiveXObject("Broker.Application");
var rc = AB.Import(0, file, "vnflow.format");
AB.RefreshAll();
AB.SaveDatabase();
WScript.Echo(rc == 0 ? "Da nap " + file : "Loi nap du lieu (ma " + rc + ") - xem import.log trong thu muc AmiBroker");
