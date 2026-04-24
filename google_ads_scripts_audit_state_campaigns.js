/**
 * Google Ads Script: read-only audit for Bomi state campaigns.
 *
 * Paste into Google Ads > Tools > Bulk actions > Scripts and run Preview.
 * This script does not mutate anything. It logs a compact summary of campaigns
 * whose names contain Illinois, Ohio, or Indiana by default.
 */

const CONFIG = {
  campaignNameContainsAny: ['Illinois', 'Ohio', 'Indiana'],
  maxRowsPerSection: 50,
};

function main() {
  const campaigns = getCampaigns_();
  if (campaigns.length === 0) {
    Logger.log(`No campaigns matched: ${CONFIG.campaignNameContainsAny.join(', ')}`);
    return;
  }

  Logger.log(`Matched ${campaigns.length} campaign(s).`);
  campaigns.forEach((campaign) => auditCampaign_(campaign));
}

function auditCampaign_(campaign) {
  Logger.log('');
  Logger.log('='.repeat(80));
  Logger.log(`${campaign.name} (${campaign.id})`);
  Logger.log(`status=${campaign.status}`);
  Logger.log(`channel=${campaign.advertisingChannelType}`);
  Logger.log(`bidding=${campaign.biddingStrategyType}`);
  Logger.log(`budget=${campaign.campaignBudget}`);
  Logger.log(`network=${JSON.stringify(campaign.networkSettings || {})}`);
  Logger.log(`geoTargetType=${JSON.stringify(campaign.geoTargetTypeSetting || {})}`);
  Logger.log(`trackingTemplate=${campaign.trackingUrlTemplate || ''}`);
  Logger.log(`finalUrlSuffix=${campaign.finalUrlSuffix || ''}`);

  logBudget_(campaign.campaignBudget);
  logLocations_(campaign.id);
  logNegativeLocations_(campaign.id);
  logAdGroups_(campaign.id);
  logKeywords_(campaign.id);
  logResponsiveSearchAds_(campaign.id);
  logCampaignAssets_(campaign.id);
}

function getCampaigns_() {
  const nameFilter = CONFIG.campaignNameContainsAny
    .map((name) => `campaign.name LIKE '%${escapeGaql_(name)}%'`)
    .join(' OR ');

  return toRows_(`
    SELECT
      campaign.id,
      campaign.name,
      campaign.status,
      campaign.resource_name,
      campaign.advertising_channel_type,
      campaign.campaign_budget,
      campaign.bidding_strategy_type,
      campaign.network_settings.target_google_search,
      campaign.network_settings.target_search_network,
      campaign.network_settings.target_content_network,
      campaign.network_settings.target_partner_search_network,
      campaign.geo_target_type_setting.positive_geo_target_type,
      campaign.geo_target_type_setting.negative_geo_target_type,
      campaign.tracking_url_template,
      campaign.final_url_suffix
    FROM campaign
    WHERE (${nameFilter})
      AND campaign.status != 'REMOVED'
    ORDER BY campaign.name
  `).map((row) => row.campaign);
}

function logBudget_(budgetResourceName) {
  const rows = toRows_(`
    SELECT
      campaign_budget.name,
      campaign_budget.amount_micros,
      campaign_budget.delivery_method,
      campaign_budget.explicitly_shared,
      campaign_budget.status
    FROM campaign_budget
    WHERE campaign_budget.resource_name = '${escapeGaql_(budgetResourceName)}'
  `);
  rows.forEach((row) => {
    const budget = row.campaignBudget;
    Logger.log(
      `budgetDetail name="${budget.name}" amount=${microsToCurrency_(budget.amountMicros)} ` +
        `delivery=${budget.deliveryMethod} shared=${budget.explicitlyShared} status=${budget.status}`
    );
  });
}

function logLocations_(campaignId) {
  const rows = limitedRows_(`
    SELECT
      campaign_criterion.criterion_id,
      campaign_criterion.negative,
      campaign_criterion.location.geo_target_constant,
      geo_target_constant.name,
      geo_target_constant.country_code,
      geo_target_constant.target_type
    FROM campaign_criterion
    WHERE campaign.id = ${Number(campaignId)}
      AND campaign_criterion.type = 'LOCATION'
      AND campaign_criterion.negative = false
      AND campaign_criterion.status != 'REMOVED'
    ORDER BY geo_target_constant.name
  `);

  Logger.log(`locations (${rows.length}${limitSuffix_()}):`);
  rows.forEach((row) => {
    const geo = row.geoTargetConstant || {};
    Logger.log(`  + ${geo.name} ${geo.countryCode || ''} ${geo.targetType || ''}`);
  });
}

function logNegativeLocations_(campaignId) {
  const rows = limitedRows_(`
    SELECT
      campaign_criterion.criterion_id,
      campaign_criterion.negative,
      campaign_criterion.location.geo_target_constant,
      geo_target_constant.name,
      geo_target_constant.country_code,
      geo_target_constant.target_type
    FROM campaign_criterion
    WHERE campaign.id = ${Number(campaignId)}
      AND campaign_criterion.type = 'LOCATION'
      AND campaign_criterion.negative = true
      AND campaign_criterion.status != 'REMOVED'
    ORDER BY geo_target_constant.name
  `);

  if (rows.length === 0) {
    Logger.log('negativeLocations: none');
    return;
  }
  Logger.log(`negativeLocations (${rows.length}${limitSuffix_()}):`);
  rows.forEach((row) => {
    const geo = row.geoTargetConstant || {};
    Logger.log(`  - ${geo.name} ${geo.countryCode || ''} ${geo.targetType || ''}`);
  });
}

function logAdGroups_(campaignId) {
  const rows = limitedRows_(`
    SELECT
      ad_group.id,
      ad_group.name,
      ad_group.status,
      ad_group.type,
      ad_group.cpc_bid_micros
    FROM ad_group
    WHERE campaign.id = ${Number(campaignId)}
      AND ad_group.status != 'REMOVED'
    ORDER BY ad_group.name
  `);

  Logger.log(`adGroups (${rows.length}${limitSuffix_()}):`);
  rows.forEach((row) => {
    const adGroup = row.adGroup;
    Logger.log(
      `  ${adGroup.name} (${adGroup.id}) status=${adGroup.status} type=${adGroup.type} ` +
        `cpc=${microsToCurrency_(adGroup.cpcBidMicros)}`
    );
  });
}

function logKeywords_(campaignId) {
  const rows = limitedRows_(`
    SELECT
      ad_group.name,
      ad_group_criterion.keyword.text,
      ad_group_criterion.keyword.match_type,
      ad_group_criterion.status,
      ad_group_criterion.negative,
      ad_group_criterion.cpc_bid_micros
    FROM ad_group_criterion
    WHERE campaign.id = ${Number(campaignId)}
      AND ad_group_criterion.type = 'KEYWORD'
      AND ad_group_criterion.status != 'REMOVED'
    ORDER BY ad_group.name, ad_group_criterion.keyword.text
  `);

  Logger.log(`keywords (${rows.length}${limitSuffix_()}):`);
  rows.forEach((row) => {
    const criterion = row.adGroupCriterion;
    const keyword = criterion.keyword;
    const sign = criterion.negative ? '-' : '+';
    Logger.log(
      `  ${sign} [${row.adGroup.name}] ${keyword.matchType} "${keyword.text}" ` +
        `status=${criterion.status} cpc=${microsToCurrency_(criterion.cpcBidMicros)}`
    );
  });
}

function logResponsiveSearchAds_(campaignId) {
  const rows = limitedRows_(`
    SELECT
      ad_group.name,
      ad_group_ad.status,
      ad_group_ad.ad.id,
      ad_group_ad.ad.final_urls,
      ad_group_ad.ad.responsive_search_ad.path1,
      ad_group_ad.ad.responsive_search_ad.path2,
      ad_group_ad.ad.responsive_search_ad.headlines,
      ad_group_ad.ad.responsive_search_ad.descriptions
    FROM ad_group_ad
    WHERE campaign.id = ${Number(campaignId)}
      AND ad_group_ad.status != 'REMOVED'
      AND ad_group_ad.ad.type = 'RESPONSIVE_SEARCH_AD'
    ORDER BY ad_group.name, ad_group_ad.ad.id
  `);

  Logger.log(`responsiveSearchAds (${rows.length}${limitSuffix_()}):`);
  rows.forEach((row) => {
    const adGroupAd = row.adGroupAd;
    const ad = adGroupAd.ad;
    const rsa = ad.responsiveSearchAd || {};
    Logger.log(
      `  [${row.adGroup.name}] ad=${ad.id} status=${adGroupAd.status} ` +
        `finalUrls=${JSON.stringify(ad.finalUrls || [])} path=${rsa.path1 || ''}/${rsa.path2 || ''}`
    );
    Logger.log(`    headlines=${summarizeTextAssets_(rsa.headlines || [])}`);
    Logger.log(`    descriptions=${summarizeTextAssets_(rsa.descriptions || [])}`);
  });
}

function logCampaignAssets_(campaignId) {
  const rows = limitedRows_(`
    SELECT
      campaign_asset.field_type,
      campaign_asset.status,
      asset.id,
      asset.name,
      asset.type,
      asset.final_urls,
      asset.sitelink_asset.link_text,
      asset.callout_asset.callout_text,
      asset.structured_snippet_asset.header,
      asset.structured_snippet_asset.values
    FROM campaign_asset
    WHERE campaign.id = ${Number(campaignId)}
      AND campaign_asset.status != 'REMOVED'
    ORDER BY campaign_asset.field_type, asset.id
  `);

  if (rows.length === 0) {
    Logger.log('campaignAssets: none');
    return;
  }
  Logger.log(`campaignAssets (${rows.length}${limitSuffix_()}):`);
  rows.forEach((row) => {
    const campaignAsset = row.campaignAsset;
    const asset = row.asset || {};
    Logger.log(
      `  ${campaignAsset.fieldType} ${asset.type} id=${asset.id} status=${campaignAsset.status} ` +
        `summary="${assetSummary_(asset)}"`
    );
  });
}

function summarizeTextAssets_(assets) {
  return assets.map((asset) => {
    const pin = asset.pinnedField ? ` pinned=${asset.pinnedField}` : '';
    return `"${asset.text}"${pin}`;
  }).join(' | ');
}

function assetSummary_(asset) {
  if (asset.sitelinkAsset) {
    return `${asset.sitelinkAsset.linkText} -> ${JSON.stringify(asset.finalUrls || [])}`;
  }
  if (asset.calloutAsset) {
    return asset.calloutAsset.calloutText;
  }
  if (asset.structuredSnippetAsset) {
    return `${asset.structuredSnippetAsset.header}: ${(asset.structuredSnippetAsset.values || []).join(', ')}`;
  }
  return asset.name || '';
}

function limitedRows_(query) {
  return toRows_(`${query} LIMIT ${Number(CONFIG.maxRowsPerSection)}`);
}

function limitSuffix_() {
  return `, max ${CONFIG.maxRowsPerSection}`;
}

function toRows_(query) {
  const iterator = AdsApp.search(query.replace(/\s+/g, ' ').trim(), { apiVersion: 'v24' });
  const rows = [];
  while (iterator.hasNext()) {
    rows.push(iterator.next());
  }
  return rows;
}

function microsToCurrency_(micros) {
  if (micros === undefined || micros === null || micros === '') {
    return '';
  }
  return `$${(Number(micros) / 1000000).toFixed(2)}`;
}

function escapeGaql_(value) {
  return String(value).replace(/\\/g, '\\\\').replace(/'/g, "\\'");
}
