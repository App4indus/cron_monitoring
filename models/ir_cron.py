# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
import requests
from openerp.exceptions import ValidationError
import logging

LOG = logging.getLogger(__name__)

class a4i_monitoring_cron(models.Model):
    _inherit = 'ir.cron'


    # ===========================================================================
    # COLUMNS
    # ===========================================================================

    a4i_sensor_active = fields.Boolean(string='Active sensor', help='Sensor is enabled or not', copy=False)
    a4i_sensor_endpoint = fields.Char(string='Sensor endpoint', help='Endpoint of the sensor (URL). This url will called once the CRON job is finished without errors.')

    @api.onchange('a4i_sensor_endpoint')
    def _onchange_a4i_sensor_endpoint(self):
        """
        Check URL validity
        return: boolean
        """
        if self.a4i_sensor_endpoint:
            if self.a4i_sensor_endpoint.startswith('http://') or self.a4i_sensor_endpoint.startswith('https://'):
                return True
            else:
                raise ValidationError(_('Invalid URL: should start with http:// or https:// ...'))

    @api.multi
    def push_uptime_kuma(self):
        """
        Push the sensor state to Uptime Kuma
        return: boolean
        """
        if self.a4i_sensor_endpoint:
            url = self.a4i_sensor_endpoint
        else:
            return ValidationError(_('Sensor endpoint is not defined'))
        
        try:
            LOG.info('Pushing the sensor state to Uptime Kuma: %s' % url)
            response = requests.get(url)

            if response.status_code == 200:
                return True
            else:
                LOG.error('Error while pushing the sensor state to Uptime Kuma: %s' % response.text)
                return False
            
        except requests.exceptions.RequestException as e:
            LOG.error(e)
            return False
        
    @api.model
    def _callback(self, model_name, method_name, args, job_id):
        """
        Override the callback method to update the sensor state
        """
        res = False
        try:
            res = super(a4i_monitoring_cron, self)._callback(model_name, method_name, args, job_id)
        except Exception as e:
            LOG.error(e)

        job_rc = self.browse(job_id)
        if res is None and job_rc and job_rc.a4i_sensor_active:
            job_rc.push_uptime_kuma()

        return res

    @api.multi
    def run_manually(self):
        """
        Override the run_manually method to update the sensor state
        """
        res, history = super(a4i_monitoring_cron, self).run_manually()

        if res is None and self.a4i_sensor_active:
            self.push_uptime_kuma()
                
        return res, history
