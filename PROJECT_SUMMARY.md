# AWS S3 Block Public Access Custom Resource

## Resumen del Proyecto

Este proyecto proporciona un Custom Resource de CloudFormation para gestionar la configuración de S3 Block Public Access a nivel de cuenta AWS. La solución utiliza código Python embebido directamente en el template de CloudFormation para máxima simplicidad y facilidad de despliegue.

## Funcionalidades Principales

- **Implementación Simple**: Función Lambda de 192 líneas sin clases ni abstracciones complejas
- **Código Embebido**: Código Python embebido directamente en el template de CloudFormation
- **Permisos Mínimos**: Utiliza solo los permisos requeridos para S3 y SNS
- **Configuración Única**: Solo procesa operaciones CREATE, ignora UPDATE/DELETE por seguridad
- **Operaciones Idempotentes**: Solo aplica cambios cuando el estado actual difiere del deseado
- **Notificaciones SNS**: Notificaciones opcionales para escenarios de éxito/fallo
- **Enfoque de Seguridad**: Las configuraciones BPA nunca se eliminan o modifican después de la configuración inicial
- **Manejo Integral de Errores**: Maneja errores de API de AWS con mensajes amigables

## Estructura del Proyecto

```
├── src/
│   └── lambda_function.py          # Función Lambda optimizada
├── tests/
│   └── test_lambda_function.py     # Pruebas unitarias
├── requirements.md                 # Requerimientos del proyecto
├── design.md                      # Documentación de diseño
├── tasks.md                       # Tareas de implementación
├── cloudformation-template-generator.py  # Generador de templates
├── s3-bpa-custom-resource.json    # Template CloudFormation generado (JSON)
├── s3-bpa-custom-resource.yaml    # Template CloudFormation generado (YAML)
└── README.md                      # Instrucciones de uso
```

## Requerimientos Cumplidos

✅ **Configuración de S3 Block Public Access**: Habilita automáticamente todas las configuraciones BPA a nivel de cuenta  
✅ **Template CloudFormation Simple**: Template generado con código embebido, sin dependencias externas  
✅ **Permisos Mínimos**: Solo permisos necesarios para S3 Control, STS y SNS  
✅ **Configuración Básica**: Configuración hardcodeada para máxima seguridad (todas las opciones habilitadas)

## Cómo Ejecutar el Proyecto

### 1. Clonar el Repositorio
```bash
git clone <repository-url>
cd aws-cloudformation-custom-resource-bpa-account
```

### 2. Ejecutar Pruebas Unitarias
```bash
# Ejecutar todas las pruebas
python -m pytest tests/ -v

# O ejecutar el archivo de pruebas directamente
python tests/test_lambda_function.py
```

### 3. Generar Templates CloudFormation
```bash
# Generar los templates JSON y YAML
python cloudformation-template-generator.py
```

Esto generará:
- `s3-bpa-custom-resource.json`
- `s3-bpa-custom-resource.yaml`

### 4. Validar el Código Embebido (Opcional)
```bash
# Ejecutar validación del código embebido
python test_embedded_logic.py
```

### 5. Desplegar el Template CloudFormation

#### Opción A: AWS CLI
```bash
# Desplegar con notificaciones SNS (opcional)
aws cloudformation create-stack \
  --stack-name s3-bpa-protection \
  --template-body file://s3-bpa-custom-resource.yaml \
  --parameters ParameterKey=NotificationTopicArn,ParameterValue=arn:aws:sns:region:account:topic \
  --capabilities CAPABILITY_IAM

# Desplegar sin notificaciones
aws cloudformation create-stack \
  --stack-name s3-bpa-protection \
  --template-body file://s3-bpa-custom-resource.yaml \
  --capabilities CAPABILITY_IAM
```

#### Opción B: AWS Console
1. Ir a CloudFormation en AWS Console
2. Crear nuevo stack
3. Subir el archivo `s3-bpa-custom-resource.yaml`
4. Configurar parámetros (NotificationTopicArn es opcional)
5. Revisar y crear stack

### 6. Verificar el Despliegue
```bash
# Verificar estado del stack
aws cloudformation describe-stacks --stack-name s3-bpa-protection

# Verificar configuración BPA aplicada
aws s3control get-public-access-block --account-id <your-account-id>
```

## Componentes del Template CloudFormation

### Parámetros
- `NotificationTopicArn`: ARN del topic SNS para notificaciones (opcional)

### Recursos
- **IAM Role**: Permisos mínimos para operaciones S3 Control, STS y SNS
- **Lambda Function**: Código Python embebido
- **Custom Resource**: Recurso de configuración S3 BPA con integración SNS

### Outputs
- ID de cuenta donde se configuró BPA
- Configuraciones BPA actuales
- Flag de cambio de configuración
- Timestamp de última actualización

## Funciones Principales de la Lambda

- `get_account_id()`: Obtiene el ID de cuenta AWS desde STS
- `get_current_bpa_config()`: Recupera configuración BPA actual usando S3 Control API
- `apply_bpa_config()`: Aplica nueva configuración BPA usando S3 Control API
- `configs_equal()`: Compara configuraciones para idempotencia
- `handle_create()`: Manejador de operaciones CREATE con integración SNS
- `send_response()`: Envía respuesta de vuelta a CloudFormation

## Operaciones Soportadas

- **CREATE**: Aplica configuración BPA si difiere del estado actual, envía notificaciones SNS
- **UPDATE**: Ignorado por seguridad (retorna SUCCESS sin acción)
- **DELETE**: Ignorado por seguridad (retorna SUCCESS sin acción)