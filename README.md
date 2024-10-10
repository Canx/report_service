# report_service

## Installation

```
sudo apt install unoconv
sudo pip install -r requirements
```

## Execution

```
start_service.sh
```

## Client REST URL

POST to http://server:port/generate

Port is 8001 by default.

## Client payload

JSON format.

template, output_format and data are required keys.

template must be a base64 docx file.

output_format must be 'docx' or 'pdf'.

Inside data complex json structure can be nested.

```
{
    "template": "<Base64 docx file>",
    "output_format": "<docx | pdf>",
    "data": {
        "nombre": "Empresa XYZ",
        "fecha": "2024-10-08",
        "usuarios": [
            {"nombre": "Juan", "edad": 28, "ciudad": "Madrid"},
            {"nombre": "Ana", "edad": 22, "ciudad": "Barcelona"},
            {"nombre": "Pedro", "edad": 30, "ciudad": "Sevilla"}
        ]
    }
}
```

## Client output

PDF or DOCX report file.
